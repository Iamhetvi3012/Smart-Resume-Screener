"""
Comprehensive Resume Parser using Instructor Library
This module provides structured extraction of resume data using LLMs and Pydantic models.
"""

import instructor
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from groq import Groq
import logging
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Simplified Pydantic Models for Resume Components


class ExternalLinks(BaseModel):
    """External profile links and websites."""

    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Personal portfolio/website URL")
    twitter: Optional[str] = Field(None, description="Twitter profile URL")
    leetcode: Optional[str] = Field(None, description="LeetCode profile URL")
    kaggle: Optional[str] = Field(None, description="Kaggle profile URL")
    hackerrank: Optional[str] = Field(None, description="HackerRank profile URL")
    medium: Optional[str] = Field(None, description="Medium profile URL")
    researchgate: Optional[str] = Field(None, description="ResearchGate profile URL")

    other: Optional[List[str]] = Field(
        default_factory=list, description="Other relevant links"
    )


class ContactInfo(BaseModel):
    """Basic contact information."""

    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State/Country")


class Education(BaseModel):
    """Educational qualification."""

    institution: str = Field(..., description="School/University name")
    degree: str = Field(..., description="Degree obtained")
    marks: Optional[str] = Field(None, description="Overall marks/cgpa obtained")
    field_of_study: Optional[str] = Field(None, description="Major/Field of study")
    graduation_year: Optional[str] = Field(None, description="Graduation year or date")


class WorkExperience(BaseModel):
    """Work experience entry."""

    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job title")
    duration: Optional[str] = Field(
        None, description="Duration (e.g., '2020-2023' or '2 years')"
    )
    description: Optional[str] = Field(
        None,
        description="Brief job description and achievements. remove corporate jargon . make it short to the point",
    )


class Project(BaseModel):
    """Project details."""

    name: Optional[str] = Field(..., description="Project name")
    description: str = Field(
        ...,
        description="Project description in very short summary. Remove corporate jargon . make it short to the point",
    )
    skills: List[str] = Field(
        default_factory=list,
        description="Technologies used or skills developed. Tech stack ,skills,services etc. example -AWS, GCP, Docker, Kubernetes, React, Node.js, Python, machine learning,mongdb , model building etc",
    )
    url: Optional[str] = Field(None, description="Project URL/link")


class Certification(BaseModel):
    """Certification details."""

    name: str = Field(..., description="Certification name")
    issuer: str = Field(..., description="Issuing organization")
    date: Optional[str] = Field(None, description="Issue date or year")


class ExtracurricularActivity(BaseModel):
    """Extracurricular activities /club society work etc"""

    name: str = Field(..., description="Activity name")
    role: Optional[str] = Field(None, description="Role/position held")
    duration: Optional[str] = Field(None, description="Duration of involvement")
    description: Optional[str] = Field(
        None, description="Brief description of the activity"
    )


# ranking awards honors etc
class AwardHonor(BaseModel):
    """Awards, honors, rankings etc."""

    title: str = Field(..., description="Title of the award/honor")
    issuer: Optional[str] = Field(None, description="Issuing organization")
    description: Optional[str] = Field(
        None, description="Brief description of the award/honor"
    )


class Resume(BaseModel):
    """Simplified resume data structure."""

    # Basic Information
    full_name: str = Field(..., description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State/Country")

    # External Links
    external_links: Optional[ExternalLinks] = Field(
        None,
        description="linkedin, github, portfolio, and other professional links. For other links Mention what link is it (e.g., Leetcode, Kaggle, Twitter, etc.)",
    )
    # Skills,tech stack

    # Experience
    work_experience: List[WorkExperience] = Field(
        default_factory=list, description="Work experience history"
    )

    # Education
    education: List[Education] = Field(
        default_factory=list, description="Educational background"
    )

    # Projects
    projects: List[Project] = Field(
        default_factory=list, description="Notable projects.Summary in short"
    )

    # Certifications
    certifications: List[Certification] = Field(
        default_factory=list, description="Professional certifications"
    )

    # Extracurricular Activities
    extracurricular_activities: List[ExtracurricularActivity] = Field(
        default_factory=list, description="Extracurricular activities"
    )
    # Awards and Honors
    awards_honors: List[AwardHonor] = Field(
        default_factory=list, description="Awards, honors, rankings etc."
    )
    skills: List[str] = Field(
        default_factory=list,
        description="List of technical and professional skills, tech stack used, languages known , services known (AWS Aure Pinecone etc)etc. Include everything mentioned by user directly  and any skill or tech stack  which the user may have missed but can be inferred from other parts of the resume like project publication certification etc.",
    )

    # Publications
    publications: List[str] = Field(
        default_factory=list, description="List of publications"
    )


class ResumeParser:
    """Resume parser class using Instructor for structured extraction from text."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "openai/gpt-oss-120b", #using openai/gpt-oss-120b
        temperature: float = 0.1,
    ):
        # Initialize Groq client and patch it with Instructor
        groq_client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
        self.model = model
        self.temperature = temperature
        logger.info(f"Initialized ResumeParser with Groq model: {model}")

    def parse_resume(self, resume_text: str) -> Resume:
        """Parse resume text into structured data."""

        system_prompt = """
        You are an expert resume parser. Extract information from resumes accurately and structure it cleanly.
        
        extract as per the schema given below:
        """

        user_prompt = f"""
        Parse this resume and extract the information:
        
        RESUME TEXT:
        {resume_text}
       
        """

        try:
            parsed_resume = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_model=Resume,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=3,
            )

            logger.info("Resume parsing completed successfully")
            return parsed_resume

        except Exception as e:
            logger.error(f"Error during resume parsing: {e}")
            raise

    def export_to_json(self, resume: Resume, file_path: str = None) -> str:
        """Export parsed resume to JSON format."""
        json_data = resume.model_dump(exclude_none=True)
        json_string = json.dumps(json_data, indent=2, default=str)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_string)

        return json_string
