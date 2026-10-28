import hashlib
import re
from typing import List, Optional
from app.schemas.knowledge import DocumentChunk

DEFAULT_CHUNK_SIZE_CHARS = 1800  # ~450-500 tokens
DEFAULT_OVERLAP_CHARS = 250      # ~60-75 tokens


def split_into_semantic_segments(text: str) -> List[str]:
    """Split raw text into paragraphs, preserving blank lines as natural separators."""
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    segments: List[str] = []

    for para in raw_paragraphs:
        # If paragraph itself is reasonably sized, keep it intact
        if len(para) <= DEFAULT_CHUNK_SIZE_CHARS:
            segments.append(para)
        else:
            # Split overly long paragraphs by sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current_sentence_group = []
            current_len = 0
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current_len + len(sentence) > DEFAULT_CHUNK_SIZE_CHARS and current_sentence_group:
                    segments.append(" ".join(current_sentence_group))
                    current_sentence_group = [sentence]
                    current_len = len(sentence)
                else:
                    current_sentence_group.append(sentence)
                    current_len += len(sentence) + 1
            if current_sentence_group:
                segments.append(" ".join(current_sentence_group))

    return segments


def chunk_text(
    text: str,
    target_size: int = DEFAULT_CHUNK_SIZE_CHARS,
    overlap_size: int = DEFAULT_OVERLAP_CHARS,
) -> List[str]:
    """
    Sliding window chunker respecting semantic boundaries.
    Ensures each chunk does not cut words or sentences in half where possible.
    """
    segments = split_into_semantic_segments(text)
    if not segments:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for segment in segments:
        seg_len = len(segment)
        if current_len + seg_len > target_size and current_chunk:
            combined = "\n\n".join(current_chunk).strip()
            chunks.append(combined)

            # Build overlap from trailing content
            overlap_segments = []
            accumulated_overlap = 0
            for seg in reversed(current_chunk):
                accumulated_overlap += len(seg)
                overlap_segments.insert(0, seg)
                if accumulated_overlap >= overlap_size:
                    break

            current_chunk = overlap_segments + [segment]
            current_len = sum(len(s) for s in current_chunk) + (len(current_chunk) - 1) * 2
        else:
            current_chunk.append(segment)
            current_len += seg_len + 2

    if current_chunk:
        combined = "\n\n".join(current_chunk).strip()
        # Avoid duplicate trailing chunk if identical to previous
        if not chunks or combined != chunks[-1]:
            chunks.append(combined)

    return chunks


def create_document_chunks(
    text: str,
    document_id: str,
    source_name: str,
    scope: str = "shared",
    topic: str = "General",
    page_number: Optional[int] = None,
) -> List[DocumentChunk]:
    """Generate structured DocumentChunk instances with stable IDs and provenance."""
    raw_chunks = chunk_text(text)
    total_chunks = len(raw_chunks)
    doc_chunks: List[DocumentChunk] = []

    for idx, chunk_content in enumerate(raw_chunks):
        chunk_id = f"{document_id}_c{idx:03d}"
        content_hash = hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()

        doc_chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                source_name=source_name,
                scope=scope,
                topic=topic,
                chunk_index=idx,
                total_chunks=total_chunks,
                text=chunk_content,
                content_hash=content_hash,
                page_number=page_number,
            )
        )

    return doc_chunks

