from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.profile import CandidateProfile, JobRequirements


class DocumentStats(BaseModel):
    resume_char_count: int = Field(default=0, description="Character count of extracted resume text")
    job_description_char_count: int = Field(default=0, description="Character count of extracted job description text")
    resume_filename: Optional[str] = Field(None, description="Original filename of resume if uploaded")
    job_description_filename: Optional[str] = Field(None, description="Original filename of job description if uploaded")


class DocumentParseResponse(BaseModel):
    candidate_profile: CandidateProfile = Field(..., description="Structured candidate profile")
    job_requirements: JobRequirements = Field(..., description="Structured job requirements")
    extraction_method: str = Field(..., description="'groq' or 'heuristic_fallback'")
    warnings: List[str] = Field(default_factory=list, description="Parsing or extraction warnings")
    stats: DocumentStats = Field(default_factory=DocumentStats, description="Document metrics")


class TextParseRequest(BaseModel):
    resume_text: str = Field(..., min_length=20, description="Raw text of candidate resume")
    job_description_text: str = Field(..., min_length=20, description="Raw text of job description")
