from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Represents a chunked slice of reference evidence."""
    chunk_id: str = Field(..., description="Unique deterministic identifier (e.g. doc_id_c001)")
    document_id: str = Field(..., description="ID of the parent document")
    source_name: str = Field(..., description="Human-readable name or title of the source")
    scope: str = Field(..., description="Evidence scope: 'shared' (technical corpus) or 'job_specific'")
    topic: str = Field(..., description="Primary topic or domain (e.g. 'FastAPI Concurrency')")
    chunk_index: int = Field(..., description="0-indexed position within the document")
    total_chunks: int = Field(..., description="Total number of chunks in the document")
    text: str = Field(..., description="Textual body of the chunk")
    content_hash: str = Field(..., description="SHA-256 hash of the chunk text for verification")
    page_number: Optional[int] = Field(None, description="Source page number if available")


class IngestDocumentRequest(BaseModel):
    """Request payload for manual text document ingestion."""
    document_id: Optional[str] = Field(None, description="Optional custom ID; slugified from title if omitted")
    source_name: str = Field(..., min_length=3, description="Title of the source document")
    scope: str = Field(default="shared", description="'shared' or 'job_specific'")
    topic: str = Field(..., min_length=2, description="Domain topic for indexing and filtering")
    text: str = Field(..., min_length=50, description="Full text content of the document")


class IngestResponse(BaseModel):
    """Summary of document ingestion into ChromaDB."""
    document_id: str
    source_name: str
    scope: str
    topic: str
    chunks_created: int
    total_characters: int
    content_hash: str
    status: str = Field(..., description="'ingested' | 'already_indexed' | 'updated'")
    message: str


class SearchRequest(BaseModel):
    """RAG similarity query parameters."""
    query: str = Field(..., min_length=3, description="Search query or interview topic")
    scope: Optional[str] = Field(None, description="Optional scope filter ('shared' or 'job_specific')")
    topic: Optional[str] = Field(None, description="Optional topic filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class SearchResultItem(BaseModel):
    """Individual retrieved evidence chunk with similarity metadata."""
    chunk_id: str
    document_id: str
    source_name: str
    scope: str
    topic: str
    chunk_index: int
    text: str
    similarity_score: float = Field(..., description="Normalized cosine similarity (0.0 to 1.0)")
    distance: float = Field(..., description="Raw vector distance from ChromaDB")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Collection of retrieved evidence chunks."""
    query: str
    total_results: int
    scope_filter: Optional[str] = None
    topic_filter: Optional[str] = None
    results: List[SearchResultItem]


class IndexedDocumentSummary(BaseModel):
    """Metadata summary of an indexed document in the vector store."""
    document_id: str
    source_name: str
    scope: str
    topic: str
    chunks_count: int
    content_hash: str

