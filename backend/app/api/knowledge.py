import os
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from app.schemas.knowledge import (
    IndexedDocumentSummary,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.parser import parse_document
from app.services.retriever import KnowledgeRetriever

router = APIRouter()
retriever = KnowledgeRetriever()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a reference document into ChromaDB (via file or raw text)",
)
async def ingest_document_endpoint(
    file: Optional[UploadFile] = File(None, description="Optional PDF, DOCX, or TXT file"),
    text: Optional[str] = Form(None, description="Raw text content if not uploading a file"),
    source_name: Optional[str] = Form(None, description="Human-readable title of the document"),
    scope: str = Form("shared", description="'shared' or 'job_specific'"),
    topic: str = Form("General", description="Domain topic for indexing"),
    document_id: Optional[str] = Form(None, description="Custom document ID"),
):
    """
    Ingest trusted technical reference or job-specific reference document into ChromaDB.
    Validates content hash to ensure idempotent ingestion.
    """
    extracted_text = ""
    effective_source_name = source_name or ""

    if file and file.filename:
        effective_source_name = effective_source_name or file.filename
        try:
            content_bytes = await file.read()
            extracted_text = parse_document(content_bytes, file.filename)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse reference document: {str(e)}",
            )
    elif text and text.strip():
        extracted_text = text.strip()
        effective_source_name = effective_source_name or "Custom Text Reference"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a document file or non-empty text must be provided.",
        )

    try:
        response = retriever.ingest_document(
            text=extracted_text,
            source_name=effective_source_name,
            scope=scope,
            topic=topic,
            document_id=document_id,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.get(
    "/documents",
    response_model=List[IndexedDocumentSummary],
    status_code=status.HTTP_200_OK,
    summary="List all indexed reference documents in ChromaDB",
)
def list_documents_endpoint():
    """Returns metadata summaries for all documents currently indexed in ChromaDB."""
    try:
        return retriever.list_documents()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect RAG similarity retrieval independently",
)
def search_knowledge_endpoint(payload: SearchRequest):
    """
    Query indexed knowledge base using local vector similarity.
    Supports scope and topic filtering without invoking the LLM.
    """
    try:
        response = retriever.search(
            query=payload.query,
            scope=payload.scope,
            topic=payload.topic,
            top_k=payload.top_k,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an indexed document and its chunks",
)
def delete_document_endpoint(document_id: str):
    """Safely delete all vector chunks associated with document_id."""
    deleted = retriever.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in index.",
        )
    return {"status": "deleted", "document_id": document_id}


@router.post(
    "/seed-defaults",
    status_code=status.HTTP_200_OK,
    summary="Seed default curated reference documents into ChromaDB",
)
def seed_default_knowledge():
    """
    Scans knowledge_base/shared/ and knowledge_base/job_specific/ directories
    and ingests all markdown documents idempotently.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge_base"))
    seeded_docs = []

    shared_dir = os.path.join(base_dir, "shared")
    job_dir = os.path.join(base_dir, "job_specific")

    for dir_path, scope in [(shared_dir, "shared"), (job_dir, "job_specific")]:
        if not os.path.exists(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(dir_path, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Derive clean title from filename or first header
                title_line = [l.strip("# ").strip() for l in content.splitlines() if l.startswith("#")]
                source_name = title_line[0] if title_line else fname.replace("_", " ").replace(".md", "").title()
                topic = "Architecture" if "system" in fname or "platform" in fname else ("Frontend" if "react" in fname else "Backend")

                doc_id = f"doc_{os.path.splitext(fname)[0]}"
                ingest_res = retriever.ingest_document(
                    text=content,
                    source_name=source_name,
                    scope=scope,
                    topic=topic,
                    document_id=doc_id,
                )
                seeded_docs.append(ingest_res)

    return {
        "status": "completed",
        "total_seeded": len(seeded_docs),
        "documents": seeded_docs,
    }

