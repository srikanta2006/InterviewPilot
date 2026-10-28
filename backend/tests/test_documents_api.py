import io
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import app

client = TestClient(app)

SAMPLE_RESUME = """
David Kim
david.kim@example.com | +1 (555) 019-2834 | Seattle, WA

Summary:
Full-Stack Engineer with 5 years experience in Python, FastAPI, React, and cloud architectures.

Experience:
Software Engineer - CloudScale Corp (2022 - Present)
- Built high-performance microservices using FastAPI, Redis, and PostgreSQL.
- Implemented responsive frontend dashboards in React and TailwindCSS.

Education:
B.S. in Software Engineering - University of Washington

Technical Skills:
Python, FastAPI, React, TypeScript, SQL, Docker, AWS, Git
"""

SAMPLE_JOB = """
Senior Full-Stack Engineer
InnovateTech | Seattle, WA

Role Overview:
Join our engineering team to design and scale AI-driven applications.

Key Requirements:
- 4+ years proficiency in Python and modern frameworks like FastAPI.
- Frontend development experience with React.
- Strong grounding in System Design, REST APIs, and database modeling.
- Experience with Docker and containerization.

Responsibilities:
- Build reliable RESTful APIs and modern frontend user experiences.
- Optimize database queries and background workflows.
"""


def test_parse_text_endpoint_success():
    response = client.post(
        "/api/documents/parse-text",
        json={
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "candidate_profile" in data
    assert "job_requirements" in data
    assert data["candidate_profile"]["full_name"] == "David Kim"
    assert data["candidate_profile"]["email"] == "david.kim@example.com"
    assert "Python" in data["candidate_profile"]["skills"]
    assert "FastAPI" in data["candidate_profile"]["skills"]
    assert len(data["job_requirements"]["required_skills"]) > 0


def test_parse_multipart_with_form_text():
    response = client.post(
        "/api/documents/parse",
        data={
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_profile"]["full_name"] == "David Kim"
    assert data["stats"]["resume_char_count"] > 100
    assert data["stats"]["job_description_char_count"] > 100


def test_parse_multipart_with_files():
    resume_bytes = SAMPLE_RESUME.encode("utf-8")
    job_bytes = SAMPLE_JOB.encode("utf-8")

    response = client.post(
        "/api/documents/parse",
        files={
            "resume_file": ("resume.txt", resume_bytes, "text/plain"),
            "job_description_file": ("job_spec.txt", job_bytes, "text/plain"),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["resume_filename"] == "resume.txt"
    assert data["stats"]["job_description_filename"] == "job_spec.txt"


def test_parse_missing_resume_returns_400():
    response = client.post(
        "/api/documents/parse",
        data={"job_description_text": SAMPLE_JOB},
    )
    assert response.status_code == 400
    assert "Resume is required" in response.json()["detail"]


def test_parse_missing_job_returns_400():
    response = client.post(
        "/api/documents/parse",
        data={"resume_text": SAMPLE_RESUME},
    )
    assert response.status_code == 400
    assert "Job description is required" in response.json()["detail"]


def test_parse_unsupported_file_extension():
    response = client.post(
        "/api/documents/parse",
        files={
            "resume_file": ("malicious.exe", b"invalid executable payload" * 10, "application/octet-stream"),
        },
        data={"job_description_text": SAMPLE_JOB},
    )
    assert response.status_code == 400
    assert "Resume error: Unsupported file format" in response.json()["detail"]


def test_no_secret_leakage_in_response():
    settings = get_settings()
    response = client.post(
        "/api/documents/parse-text",
        json={
            "resume_text": SAMPLE_RESUME,
            "job_description_text": SAMPLE_JOB,
        },
    )
    assert response.status_code == 200
    response_text = response.text
    if settings.groq_api_key:
        assert settings.groq_api_key not in response_text
