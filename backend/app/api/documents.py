from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from app.schemas.documents import DocumentParseResponse, TextParseRequest
from app.services.extractor import DocumentExtractor
from app.services.parser import (
    CorruptDocumentError,
    DocumentParsingError,
    EmptyDocumentError,
    FileTooLargeError,
    ScannedDocumentError,
    UnsupportedDocumentError,
    parse_document,
)

router = APIRouter()
extractor = DocumentExtractor()


@router.post(
    "/parse",
    response_model=DocumentParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse candidate resume and job description from files or text",
)
async def parse_documents(
    resume_file: Optional[UploadFile] = File(None, description="Resume file (.pdf, .docx, .txt)"),
    resume_text: Optional[str] = Form(None, description="Pasted resume text content"),
    job_description_file: Optional[UploadFile] = File(None, description="Job description file (.pdf, .docx, .txt)"),
    job_description_text: Optional[str] = Form(None, description="Pasted job description text content"),
):
    """
    Parse candidate resume and job description.
    Supports either file uploads or direct text inputs for both inputs.
    Extracts validated CandidateProfile and JobRequirements schemas.
    """
    extracted_resume_text = ""
    resume_filename = None

    extracted_job_text = ""
    job_filename = None

    # 1. Resolve Resume Content
    if resume_file and resume_file.filename:
        resume_filename = resume_file.filename
        try:
            content_bytes = await resume_file.read()
            extracted_resume_text = parse_document(content_bytes, resume_file.filename)
        except (
            UnsupportedDocumentError,
            FileTooLargeError,
            EmptyDocumentError,
            ScannedDocumentError,
            CorruptDocumentError,
            DocumentParsingError,
        ) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Resume error: {str(err)}")
    elif resume_text and resume_text.strip():
        extracted_resume_text = resume_text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume is required. Upload a supported file (.pdf, .docx, .txt) or provide resume text.",
        )

    # 2. Resolve Job Description Content
    if job_description_file and job_description_file.filename:
        job_filename = job_description_file.filename
        try:
            content_bytes = await job_description_file.read()
            extracted_job_text = parse_document(content_bytes, job_description_file.filename)
        except (
            UnsupportedDocumentError,
            FileTooLargeError,
            EmptyDocumentError,
            ScannedDocumentError,
            CorruptDocumentError,
            DocumentParsingError,
        ) as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Job description error: {str(err)}")
    elif job_description_text and job_description_text.strip():
        extracted_job_text = job_description_text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is required. Upload a supported file (.pdf, .docx, .txt) or provide job description text.",
        )

    # 3. Process extraction
    try:
        response = extractor.process(
            resume_text=extracted_resume_text,
            job_text=extracted_job_text,
            resume_filename=resume_filename,
            job_filename=job_filename,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during profile extraction: {str(e)}",
        )


@router.post(
    "/parse-text",
    response_model=DocumentParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse resume and job description directly from JSON text payload",
)
def parse_text_endpoint(payload: TextParseRequest):
    """Direct JSON payload parsing for testing and programmatic clients."""
    try:
        response = extractor.process(
            resume_text=payload.resume_text,
            job_text=payload.job_description_text,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during text extraction: {str(e)}",
        )
