from typing import List, Optional
from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    title: str = Field(..., description="Job or role title")
    company: Optional[str] = Field(None, description="Company or organization name")
    duration: Optional[str] = Field(None, description="Dates or tenure of employment")
    description: Optional[str] = Field(None, description="Key duties and achievements")
    technologies: List[str] = Field(default_factory=list, description="Technologies or tools used")


class EducationItem(BaseModel):
    degree: Optional[str] = Field(None, description="Degree or qualification earned")
    institution: Optional[str] = Field(None, description="School, university, or issuing body")
    year: Optional[str] = Field(None, description="Year of completion or graduation")


class ProjectItem(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Brief description of the project")
    technologies: List[str] = Field(default_factory=list, description="Technologies applied in the project")


class CandidateProfile(BaseModel):
    full_name: Optional[str] = Field(None, description="Candidate's full name")
    name: Optional[str] = Field(None, description="Candidate's name alias")
    title: Optional[str] = Field(None, description="Current or target role title")
    email: Optional[str] = Field(None, description="Candidate contact email")
    phone: Optional[str] = Field(None, description="Candidate contact phone")
    years_of_experience: Optional[float] = Field(None, description="Estimated total years of professional experience")
    summary: Optional[str] = Field(None, description="Professional summary or bio")
    skills: List[str] = Field(default_factory=list, description="Technical and soft skills")
    experiences: List[ExperienceItem] = Field(default_factory=list, description="Work experience history")
    education: List[EducationItem] = Field(default_factory=list, description="Educational background")
    projects: List[ProjectItem] = Field(default_factory=list, description="Notable personal or work projects")
    primary_competencies: List[str] = Field(
        default_factory=list,
        description="Core competencies extracted for interview evaluation (e.g. System Design, REST APIs, Frontend React)"
    )


class JobRequirements(BaseModel):
    job_title: Optional[str] = Field(None, description="Target job title")
    title: Optional[str] = Field(None, description="Target job title alias")
    company: Optional[str] = Field(None, description="Hiring organization")
    experience_level: Optional[str] = Field(None, description="Seniority or experience level (e.g., Junior, Mid, Senior, Lead)")
    required_skills: List[str] = Field(default_factory=list, description="Must-have skills and technologies")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or preferred skills")
    core_competencies: List[str] = Field(
        default_factory=list,
        description="Key evaluation competencies matching the role requirements"
    )
    responsibilities: List[str] = Field(default_factory=list, description="Key role responsibilities")
    summary: Optional[str] = Field(None, description="Overall summary of the role")
