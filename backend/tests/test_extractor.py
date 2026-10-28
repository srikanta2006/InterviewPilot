from unittest.mock import MagicMock
import pytest
from app.schemas.profile import CandidateProfile, JobRequirements
from app.services.extractor import DocumentExtractor
from app.services.groq_client import GroqClientService

SAMPLE_RESUME = """
Jane Doe
jane.doe@example.com | (555) 123-4567 | San Francisco, CA

Professional Summary:
Versatile Full-Stack Engineer with 6+ years specializing in Python, FastAPI, React, and SQL database design.

Experience:
Senior Software Engineer - Tech Innovators Inc. (2021 - Present)
- Architected high-throughput REST APIs handling 10M+ daily events using FastAPI and Docker.
- Spearheaded frontend migration to React and TypeScript.

Education:
B.S. in Computer Science - University of California, Berkeley

Technical Skills:
Python, FastAPI, React, TypeScript, Docker, PostgreSQL, Redis, Git, Linux
"""

SAMPLE_JOB = """
Senior Python & Full-Stack Developer
Acme Corp | San Francisco, CA

About the Role:
We are seeking an experienced Senior Software Engineer to build scalable cloud microservices.

Requirements:
- 5+ years building backend services with Python, FastAPI, and PostgreSQL.
- Strong frontend proficiency with React and modern JavaScript/TypeScript.
- Experience with Docker, Kubernetes, and AWS deployment pipelines.
- Deep understanding of System Design, Data Structures, and API Security.

Responsibilities:
- Lead the architecture and implementation of critical backend features.
- Mentor junior engineers and champion clean code practices.
"""


def test_heuristic_extraction():
    extractor = DocumentExtractor(groq_service=GroqClientService(api_key=""))
    response = extractor.process(
        resume_text=SAMPLE_RESUME,
        job_text=SAMPLE_JOB,
        resume_filename="jane_resume.pdf",
        job_filename="job_spec.txt",
    )

    assert response.candidate_profile.full_name == "Jane Doe"
    assert response.candidate_profile.email == "jane.doe@example.com"
    assert "Python" in response.candidate_profile.skills
    assert "FastAPI" in response.candidate_profile.skills
    assert "React" in response.candidate_profile.skills
    assert len(response.candidate_profile.primary_competencies) > 0

    assert "Senior Python" in response.job_requirements.job_title or "Software Engineer" in response.job_requirements.job_title
    assert "Python" in response.job_requirements.required_skills
    assert len(response.job_requirements.core_competencies) > 0

    assert response.extraction_method == "heuristic_fallback"
    assert response.stats.resume_filename == "jane_resume.pdf"
    assert response.stats.resume_char_count > 100


def test_mocked_groq_extraction_success():
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True

    mock_profile = CandidateProfile(
        full_name="Jane Doe (Groq)",
        email="jane@example.com",
        skills=["Python", "FastAPI", "React"],
        primary_competencies=["Backend API", "Frontend React"],
    )

    mock_job = JobRequirements(
        job_title="Lead Architect",
        required_skills=["Python", "FastAPI"],
        core_competencies=["Distributed Systems"],
    )

    def mock_extract(system_prompt, user_prompt, response_model, **kwargs):
        if response_model == CandidateProfile:
            return mock_profile
        elif response_model == JobRequirements:
            return mock_job
        return None

    mock_groq.extract_structured_json.side_effect = mock_extract

    extractor = DocumentExtractor(groq_service=mock_groq)
    response = extractor.process(resume_text=SAMPLE_RESUME, job_text=SAMPLE_JOB)

    assert response.extraction_method == "groq"
    assert response.candidate_profile.full_name == "Jane Doe (Groq)"
    assert response.job_requirements.job_title == "Lead Architect"
    assert len(response.warnings) == 0


def test_mocked_groq_extraction_fallback_on_failure():
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True
    # Simulate LLM failure or malformed output
    mock_groq.extract_structured_json.return_value = None

    extractor = DocumentExtractor(groq_service=mock_groq)
    response = extractor.process(resume_text=SAMPLE_RESUME, job_text=SAMPLE_JOB)

    # Should fall back cleanly to heuristic extraction without crashing
    assert response.extraction_method == "heuristic_fallback"
    assert response.candidate_profile.email == "jane.doe@example.com"
    assert any("fell back" in w.lower() for w in response.warnings)
