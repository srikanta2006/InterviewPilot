import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional
from app.config import get_settings
from app.schemas.knowledge import (
    IndexedDocumentSummary,
    IngestResponse,
    SearchResponse,
    SearchResultItem,
)
from app.services.chunker import create_document_chunks
from app.services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)
COLLECTION_NAME = "interviewpilot_knowledge"


def slugify(text: str) -> str:
    """Convert a title to a clean URL/ID slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:40].strip("_")


class KnowledgeRetriever:
    """
    Manages vector indexing and inspectable RAG retrieval using ChromaDB
    and local sentence-transformers.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_persist_directory
        self.embedding_service = embedding_service or EmbeddingService()
        self._client = None
        self._collection = None

    def _get_collection(self):
        """Lazily initialize ChromaDB persistent client and collection."""
        if self._collection is not None:
            return self._collection

        import chromadb
        from chromadb.config import Settings as ChromaSettings

        os.makedirs(self.persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
        )

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_service,
            metadata={"description": "InterviewPilot trusted reference knowledge base"},
        )
        return self._collection

    def ingest_document(
        self,
        text: str,
        source_name: str,
        scope: str = "shared",
        topic: str = "General",
        document_id: Optional[str] = None,
    ) -> IngestResponse:
        """
        Idempotently ingest a reference document.
        Validates content hash to avoid duplicate embedding compute.
        """
        if not text or len(text.strip()) < 30:
            raise ValueError("Document text is too short or empty for ingestion.")

        collection = self._get_collection()
        doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        if not document_id:
            document_id = f"doc_{slugify(source_name)}"

        # Check existing chunks for this document_id
        existing = collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )

        existing_ids = existing.get("ids", [])
        if existing_ids:
            # Check if content has changed by inspecting stored doc_hash
            first_meta = existing.get("metadatas", [{}])[0]
            existing_doc_hash = first_meta.get("doc_hash", "")
            if existing_doc_hash == doc_hash:
                return IngestResponse(
                    document_id=document_id,
                    source_name=source_name,
                    scope=scope,
                    topic=topic,
                    chunks_created=len(existing_ids),
                    total_characters=len(text),
                    content_hash=doc_hash,
                    status="already_indexed",
                    message="Document is already indexed with identical content; no re-chunking required.",
                )
            else:
                # Content updated: remove old chunks first
                collection.delete(ids=existing_ids)
                status_label = "updated"
                msg = f"Updated existing document '{document_id}' with new content."
        else:
            status_label = "ingested"
            msg = f"Successfully indexed new document '{document_id}'."

        # Generate semantic chunks
        chunks = create_document_chunks(
            text=text,
            document_id=document_id,
            source_name=source_name,
            scope=scope,
            topic=topic,
        )

        if not chunks:
            raise ValueError("Failed to create any chunks from document text.")

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "source_name": c.source_name,
                "scope": c.scope,
                "topic": c.topic,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
                "content_hash": c.content_hash,
                "doc_hash": doc_hash,
            }
            for c in chunks
        ]

        # Ingest into ChromaDB
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        return IngestResponse(
            document_id=document_id,
            source_name=source_name,
            scope=scope,
            topic=topic,
            chunks_created=len(chunks),
            total_characters=len(text),
            content_hash=doc_hash,
            status=status_label,
            message=msg,
        )

    def search(
        self,
        query: str,
        scope: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5,
    ) -> SearchResponse:
        """
        Execute vector similarity query against indexed reference chunks.
        Supports scope filtering ('shared' vs 'job_specific') and topic filtering.
        """
        collection = self._get_collection()

        # Build ChromaDB metadata filter
        where_filter: Optional[Dict[str, Any]] = None
        filters = []
        if scope:
            filters.append({"scope": scope})
        if topic:
            filters.append({"topic": topic})

        if len(filters) == 1:
            where_filter = filters[0]
        elif len(filters) > 1:
            where_filter = {"$and": filters}

        # Query vector collection
        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return SearchResponse(
                query=query,
                total_results=0,
                scope_filter=scope,
                topic_filter=topic,
                results=[],
            )

        items: List[SearchResultItem] = []
        doc_ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for chunk_id, text, meta, dist in zip(doc_ids, docs, metas, distances):
            # Normalize cosine distance (typically 0.0 to 2.0) into similarity (0.0 to 1.0)
            sim_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            items.append(
                SearchResultItem(
                    chunk_id=chunk_id,
                    document_id=meta.get("document_id", ""),
                    source_name=meta.get("source_name", ""),
                    scope=meta.get("scope", "shared"),
                    topic=meta.get("topic", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    text=text,
                    similarity_score=round(sim_score, 4),
                    distance=round(dist, 4),
                    metadata=meta,
                )
            )

        return SearchResponse(
            query=query,
            total_results=len(items),
            scope_filter=scope,
            topic_filter=topic,
            results=items,
        )

    def list_documents(self) -> List[IndexedDocumentSummary]:
        """Aggregate and return summaries for all indexed documents in the store."""
        collection = self._get_collection()
        all_data = collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", [])

        docs_map: Dict[str, Dict[str, Any]] = {}
        for meta in metadatas:
            doc_id = meta.get("document_id")
            if not doc_id:
                continue
            if doc_id not in docs_map:
                docs_map[doc_id] = {
                    "document_id": doc_id,
                    "source_name": meta.get("source_name", doc_id),
                    "scope": meta.get("scope", "shared"),
                    "topic": meta.get("topic", "General"),
                    "chunks_count": 0,
                    "content_hash": meta.get("doc_hash", ""),
                }
            docs_map[doc_id]["chunks_count"] += 1

        return [IndexedDocumentSummary(**doc) for doc in docs_map.values()]

    def delete_document(self, document_id: str) -> bool:
        """Safely delete all chunks associated with a document ID."""
        collection = self._get_collection()
        existing = collection.get(where={"document_id": document_id})
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
            return True
        return False

