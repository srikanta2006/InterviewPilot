import re
from typing import List, Optional, Tuple
from app.schemas.profile import (
    CandidateProfile,
    EducationItem,
    ExperienceItem,
    JobRequirements,
    ProjectItem,
)
from app.schemas.documents import DocumentParseResponse, DocumentStats
from app.services.groq_client import GroqClientService

# Known technical keywords for heuristic extraction
COMMON_TECH_SKILLS = [
    "Python", "FastAPI", "Flask", "Django", "JavaScript", "TypeScript", "React", "Next.js",
    "Node.js", "Express", "HTML", "CSS", "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB",
    "Redis", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD",
    "REST APIs", "GraphQL", "PyTorch", "TensorFlow", "Scikit-Learn", "ChromaDB", "Linux",
    "Machine Learning", "System Design", "Microservices", "Data Structures", "Algorithms",
    "C++", "Java", "Go", "Rust", "TailwindCSS", "Pandas", "NumPy"
]


class DocumentExtractor:
    """Extracts structured candidate profile and job requirements using Groq with deterministic fallback."""

    def __init__(self, groq_service: Optional[GroqClientService] = None):
        self.groq_service = groq_service or GroqClientService()

    def extract_with_groq(
        self, resume_text: str, job_text: str
    ) -> Optional[Tuple[CandidateProfile, JobRequirements]]:
        """Attempt LLM structured extraction via Groq."""
        if not self.groq_service.is_configured:
            return None

        profile_system_prompt = (
            "You are an expert technical recruiter and resume parser. "
            "Extract structured information from the provided candidate resume into valid JSON matching this schema: "
            "{"
            "  'full_name': string or null,"
            "  'email': string or null,"
            "  'phone': string or null,"
            "  'summary': string or null,"
            "  'skills': [string],"
            "  'experiences': [{'title': string, 'company': string, 'duration': string, 'description': string, 'technologies': [string]}],"
            "  'education': [{'degree': string, 'institution': string, 'year': string}],"
            "  'projects': [{'name': string, 'description': string, 'technologies': [string]}],"
            "  'primary_competencies': [string]"
            "}."
            "Extract only factual information present in the resume. Do not fabricate details."
        )

        job_system_prompt = (
            "You are an expert technical interviewer and hiring architect. "
            "Extract structured job requirements from the provided job description into valid JSON matching this schema: "
            "{"
            "  'job_title': string or null,"
            "  'company': string or null,"
            "  'experience_level': string or null,"
            "  'required_skills': [string],"
            "  'preferred_skills': [string],"
            "  'core_competencies': [string],"
            "  'responsibilities': [string],"
            "  'summary': string or null"
            "}."
            "Extract clear, evaluatable competencies (e.g. 'Backend API Architecture', 'React State Management')."
        )

        candidate_profile = self.groq_service.extract_structured_json(
            system_prompt=profile_system_prompt,
            user_prompt=f"RESUME CONTENT:\n{resume_text}",
            response_model=CandidateProfile,
        )

        job_requirements = self.groq_service.extract_structured_json(
            system_prompt=job_system_prompt,
            user_prompt=f"JOB DESCRIPTION CONTENT:\n{job_text}",
            response_model=JobRequirements,
        )

        if candidate_profile and job_requirements:
            return candidate_profile, job_requirements
        return None

    def extract_heuristically(
        self, resume_text: str, job_text: str
    ) -> Tuple[CandidateProfile, JobRequirements]:
        """Deterministic heuristic extraction using regex and pattern matching."""
        # 1. Candidate contact details
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resume_text)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", resume_text)
        phone = phone_match.group(0) if phone_match else None

        # Full name: first non-empty line with less than 40 characters
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        full_name = lines[0] if lines and len(lines[0]) < 40 and not any(kw in lines[0].lower() for kw in ["resume", "curriculum", "cv", "page"]) else "Candidate"

        # Skills extraction
        resume_lower = resume_text.lower()
        found_skills = [skill for skill in COMMON_TECH_SKILLS if re.search(rf"\b{re.escape(skill.lower())}\b", resume_lower)]
        if not found_skills:
            found_skills = ["Software Engineering", "Problem Solving"]

        # Primary competencies: select top detected skills/domains
        competencies = found_skills[:5] if found_skills else ["General Engineering"]

        # Parse simple experience items
        experiences = []
        for i, line in enumerate(lines[:30]):
            if any(term in line.lower() for term in ["engineer", "developer", "lead", "architect", "intern", "consultant"]):
                experiences.append(
                    ExperienceItem(
                        title=line[:50],
                        company=lines[i + 1][:50] if i + 1 < len(lines) else None,
                        duration="Identified from profile",
                        description=lines[i + 2][:120] if i + 2 < len(lines) else None,
                        technologies=[s for s in found_skills if s.lower() in line.lower()][:4],
                    )
                )
            if len(experiences) >= 3:
                break

        if not experiences:
            experiences.append(
                ExperienceItem(
                    title="Software Developer",
                    company="Professional Experience",
                    duration="Present",
                    description="Extracted work experience and technical accomplishments.",
                    technologies=found_skills[:3],
                )
            )

        # Parse simple education items
        education = []
        for line in lines:
            if any(term in line.lower() for term in ["bachelor", "master", "phd", "b.s.", "m.s.", "university", "institute", "college"]):
                education.append(
                    EducationItem(
                        degree=line[:60],
                        institution="Academic Institution",
                        year=None,
                    )
                )
                if len(education) >= 2:
                    break

        candidate_profile = CandidateProfile(
            full_name=full_name,
            email=email,
            phone=phone,
            summary=f"Technical professional with proficiency in {', '.join(found_skills[:4])}.",
            skills=found_skills,
            experiences=experiences,
            education=education,
            projects=[
                ProjectItem(
                    name="Featured Technical Project",
                    description="Demonstrated technical delivery and practical implementation.",
                    technologies=found_skills[:3],
                )
            ],
            primary_competencies=competencies,
        )

        # 2. Job requirements extraction
        job_lines = [l.strip() for l in job_text.splitlines() if l.strip()]
        job_title = job_lines[0] if job_lines and len(job_lines[0]) < 60 else "Software Engineer"
        for line in job_lines[:10]:
            if any(t in line.lower() for t in ["engineer", "developer", "architect", "manager", "specialist"]):
                job_title = line[:50]
                break

        job_lower = job_text.lower()
        job_req_skills = [s for s in COMMON_TECH_SKILLS if re.search(rf"\b{re.escape(s.lower())}\b", job_lower)]
        if not job_req_skills:
            job_req_skills = ["Python", "FastAPI", "React", "REST APIs"]

        # Core competencies for evaluation
        core_competencies = list(dict.fromkeys(job_req_skills[:6] + ["System Architecture", "Code Quality"]))[:5]

        job_requirements = JobRequirements(
            job_title=job_title,
            company=None,
            experience_level="Mid-to-Senior",
            required_skills=job_req_skills,
            preferred_skills=[s for s in COMMON_TECH_SKILLS if s not in job_req_skills][:4],
            core_competencies=core_competencies,
            responsibilities=[
                "Design, implement, and maintain scalable software services.",
                "Collaborate with cross-functional teams to deliver production features.",
                "Ensure robust automated testing, code reviews, and system reliability.",
            ],
            summary=job_lines[1][:150] if len(job_lines) > 1 else "Role focused on building robust technical solutions.",
        )

        return candidate_profile, job_requirements

    def process(
        self,
        resume_text: str,
        job_text: str,
        resume_filename: Optional[str] = None,
        job_filename: Optional[str] = None,
    ) -> DocumentParseResponse:
        """Run extraction and return structured validated DocumentParseResponse."""
        warnings: List[str] = []
        stats = DocumentStats(
            resume_char_count=len(resume_text),
            job_description_char_count=len(job_text),
            resume_filename=resume_filename,
            job_description_filename=job_filename,
        )

        # Check if LLM extraction is feasible
        extracted = None
        method = "heuristic_fallback"

        if self.groq_service.is_configured:
            try:
                extracted = self.extract_with_groq(resume_text, job_text)
                if extracted:
                    method = "groq"
                else:
                    warnings.append("Groq extraction failed or timed out; fell back to deterministic heuristic parser.")
            except Exception as e:
                warnings.append(f"Groq API error ({str(e)}); fell back to deterministic heuristic parser.")
        else:
            warnings.append(
                "GROQ_API_KEY is not configured or is a placeholder. "
                "Parsed profile using deterministic local heuristic extraction."
            )

        if not extracted:
            extracted = self.extract_heuristically(resume_text, job_text)

        candidate_profile, job_requirements = extracted

        return DocumentParseResponse(
            candidate_profile=candidate_profile,
            job_requirements=job_requirements,
            extraction_method=method,
            warnings=warnings,
            stats=stats,
        )
