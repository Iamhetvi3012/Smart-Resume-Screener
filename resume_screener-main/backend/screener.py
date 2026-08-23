"""
Resume Screener using Instructor Library
This module provides structured scoring and evaluation of resumes against job requirements.
"""

import instructor
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import json
from groq import Groq
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Screening Models

class SkillMatch(BaseModel):
    """Skill matching evaluation."""
    
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Skill match score out of 10"
    )
    matched_skills: List[str] = Field(
        default_factory=list,
        description="Skills from resume that match job requirements"
    )
    missing_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="Critical skills mentioned in job description but missing in resume. "
    )
    additional_skills: Optional[List[str]] = Field(
        default_factory=list,
        description="Relevant skills candidate has beyond job requirements"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the skill match score"
    )


class ExperienceMatch(BaseModel):
    """Experience matching evaluation."""
    
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Experience relevance score out of 10. Be harsh on the rating if it does not meet upto the required expectations"
    )
    meets_requirements: bool = Field(
        ...,
        description="Whether experience meets minimum job requirements"
    )
    relevant_experience: List[str] = Field(
        default_factory=list,
        description="Work experiences that are relevant to the job"
    )
    years_of_experience: Optional[str] = Field(
        None,
        description="Estimated total years of relevant experience"
    )
    seniority_match: str = Field(
        ...,
        description="How well candidate's seniority level matches job requirements (under-qualified/appropriate/over-qualified)"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the experience match score"
    )


class EducationMatch(BaseModel):
    """Education matching evaluation."""
    
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Education match score out of 10"
    )
    meets_requirements: bool = Field(
        ...,
        description="Whether education meets minimum job requirements"
    )
    relevant_degrees: List[str] = Field(
        default_factory=list,
        description="Degrees/qualifications relevant to the job"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the education match score"
    )


class ProjectMatch(BaseModel):
    """Project portfolio evaluation."""
    
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="A score to determine if the projects are relevant and also non generic." \
        "Rate the projects critically if it seems non creative or generic slop then reduce rating " \
        "More marks if projects have innovative or new ideas or implementation." \
        "Score out of 10"
    )
    relevant_projects: List[str] = Field(
        default_factory=list,
        description="Projects that demonstrate relevant skills/experience. Keep only the projects which are similiar to what the job profile is. Be choosy in picking the projects and choose 1 always but after that choose only if you think anything else is matching"
    )
    key_technologies: List[str] = Field(
        default_factory=list,
        description="Technologies used in projects that match job requirements"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the project match score"
    )

class CulturalFit(BaseModel):
    """Cultural and soft skills evaluation."""
    
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Cultural fit and soft skills score out of 10." \
        "The scoring for this is more generous as it may be subjective . Give a general overview"
    )
    indicators: List[str] = Field(
        default_factory=list,
        description="Indicators of cultural fit from extracurriculars, leadership, etc."
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of cultural fit score"
    )


class ResumeScreeningResult(BaseModel):
    """Complete resume screening evaluation."""
    
    # Individual category scores
    skill_match: SkillMatch
    experience_match: ExperienceMatch
    education_match: EducationMatch
    project_match: ProjectMatch
    
    cultural_fit: CulturalFit
    
    # Overall evaluation
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Weighted overall compatibility score out of 10." \
        "If the candidate fails severly in any field then overall rating would drop drastically." \
        "Be critical in rating the candidate as this is a matter of choosing the perfect candidate"
    )
    
    recommendation: str = Field(
        ...,
        description="Hiring recommendation: 'Strong Match', 'Good Match', 'Potential Match', 'Weak Match', or 'Not a Match'"
    )
    
    summary: str = Field(
        ...,
        description="2-3 sentence executive summary of the candidate's fit for the role"
    )
    
    strengths: List[str] = Field(
        default_factory=list,
        description="Top 3-5 strengths of the candidate for this role"
    )
    
    concerns: List[str] = Field(
        default_factory=list,
        description="Top 3-5 concerns or gaps for this role"
    )
    
    


class ResumeScreener:
    """
    Resume screener that evaluates candidates against job requirements.
    Uses LLM with structured outputs via Instructor.
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.2,
    ):
        """
        Initialize the screener with Groq API.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Groq model to use
            temperature: Temperature for LLM (0.2 for more consistent scoring)
        """
        groq_client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
        self.model = model
        self.temperature = temperature
        logger.info(f"Initialized ResumeScreener with Groq model: {model}")
    
    def screen_resume(
        self,
        parsed_resume: Dict,
        job_title: str,
        job_description: str,
        weights: Optional[Dict[str, float]] = None
    ) -> ResumeScreeningResult:
        """
        Screen a resume against job requirements.
        
        Args:
            parsed_resume: Parsed resume data (dict from parser.py)
            job_title: Title of the job position
            job_description: Full job description including requirements
            weights: Optional custom weights for scoring categories
                    Default: {
                        'skills': 0.30,
                        'experience': 0.25,
                        'education': 0.15,
                        'projects': 0.15,
                        'cultural_fit': 0.05
                    }
        
        Returns:
            ResumeScreeningResult with detailed scoring and analysis
        """
        # Default weights if not provided
        if weights is None:
            weights = {
                'skills': 0.30,
                'experience': 0.25,
                'education': 0.15,
                'projects': 0.15,
                'cultural_fit': 0.05
            }
        
        system_prompt = """
        You are an expert technical recruiter and resume screener with deep knowledge across multiple industries.
        Your job is to evaluate how well a candidate's resume matches a job opening.
        Be crtitial in your evaluation and fair in your rating . Don't hesitate to lower scores if the candidate does not meet expectations.
        In fact lower scores are more common than high scores.
        
        EVALUATION GUIDELINES:
        1. Be objective and fair in your assessment
        2. Consider both technical skills and soft skills but prioritize technical fit
        3. Look for relevant experience, not just years
        4. Value projects and certifications that demonstrate practical skills. Value projects which are unique and show commitment to learning and coding rather than generic slop taken from github.
        5. Consider transferable skills from different domains
        6. Be realistic about skill gaps - focus on critical vs. nice-to-have
        7. Use the full 0-10 scale (don't cluster around 7-8). This is a matter of chosing a candidate so each field of rating must reflect the candidate's skills in their entirity
        8. Provide actionable, specific feedback
        9. Even if a candidate seems strong in some fields if they do not have the required skills or the experience for the job then overall rating should be low.
        SCORING SCALE:
        9-10: Exceptional match, rare to find better
        7-8: Strong match, highly qualified
        5-6: Good match, qualified with some gaps
        3-4: Potential match, significant gaps but trainable
        0-2: Poor match, major misalignment
        """
        
        # Format resume data for the prompt
        resume_summary = self._format_resume_for_screening(parsed_resume)
        
        user_prompt = f"""
        Evaluate this candidate's resume for the following position:
        
        JOB TITLE: {job_title}
        
        JOB DESCRIPTION:
        {job_description}
        
        CANDIDATE RESUME:
        {resume_summary}
        
        SCORING WEIGHTS:
        - Skills: {weights['skills']*100}%
        - Experience: {weights['experience']*100}%
        - Education: {weights['education']*100}%
        - Projects: {weights['projects']*100}%
        
        - Cultural Fit: {weights['cultural_fit']*100}%
        
        Provide a comprehensive evaluation with scores for each category and an overall assessment.
        Calculate the overall score using the weighted average of individual category scores.
        Be specific in your reasoning and provide actionable insights.
        """
        
        try:
            screening_result = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_model=ResumeScreeningResult,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=3,
            )
            
            logger.info(f"Resume screening completed. Overall score: {screening_result.overall_score}/10")
            return screening_result
            
        except Exception as e:
            logger.error(f"Error during resume screening: {e}")
            raise
    
    def _format_resume_for_screening(self, parsed_resume: Dict) -> str:
        """Format parsed resume data into a readable string for screening."""
        
        sections = []
        
        # Basic info
        sections.append(f"NAME: {parsed_resume.get('full_name', 'N/A')}")
        sections.append(f"LOCATION: {parsed_resume.get('location', 'N/A')}")
        
        # External links
        if parsed_resume.get('external_links'):
            links = parsed_resume['external_links']
            link_list = []
            if links.get('linkedin'): link_list.append(f"LinkedIn: {links['linkedin']}")
            if links.get('github'): link_list.append(f"GitHub: {links['github']}")
            if links.get('portfolio'): link_list.append(f"Portfolio: {links['portfolio']}")
            if link_list:
                sections.append("\nPROFESSIONAL LINKS:\n" + "\n".join(link_list))
        
        # Skills
        if parsed_resume.get('skills'):
            sections.append("\nSKILLS:\n" + ", ".join(parsed_resume['skills']))
        
        # Work Experience
        if parsed_resume.get('work_experience'):
            sections.append("\nWORK EXPERIENCE:")
            for exp in parsed_resume['work_experience']:
                sections.append(f"\n- {exp.get('position', 'N/A')} at {exp.get('company', 'N/A')}")
                if exp.get('duration'):
                    sections.append(f"  Duration: {exp['duration']}")
                if exp.get('description'):
                    sections.append(f"  {exp['description']}")
        
        # Education
        if parsed_resume.get('education'):
            sections.append("\nEDUCATION:")
            for edu in parsed_resume['education']:
                sections.append(f"\n- {edu.get('degree', 'N/A')} in {edu.get('field_of_study', 'N/A')}")
                sections.append(f"  {edu.get('institution', 'N/A')}")
                if edu.get('graduation_year'):
                    sections.append(f"  Graduated: {edu['graduation_year']}")
                if edu.get('marks'):
                    sections.append(f"  Marks: {edu['marks']}")
        
        # Projects
        if parsed_resume.get('projects'):
            sections.append("\nPROJECTS:")
            for proj in parsed_resume['projects']:
                sections.append(f"\n- {proj.get('name', 'Unnamed Project')}")
                if proj.get('description'):
                    sections.append(f"  {proj['description']}")
                if proj.get('skills'):
                    sections.append(f"  Technologies: {', '.join(proj['skills'])}")
        
        
        # Extracurricular Activities
        if parsed_resume.get('extracurricular_activities'):
            sections.append("\nEXTRACURRICULAR ACTIVITIES:")
            for activity in parsed_resume['extracurricular_activities']:
                sections.append(f"- {activity.get('name', 'N/A')} ({activity.get('role', 'N/A')})")
        
        # Awards and Honors
        if parsed_resume.get('awards_honors'):
            sections.append("\nAWARDS & HONORS:")
            for award in parsed_resume['awards_honors']:
                sections.append(f"- {award.get('title', 'N/A')}")
        
        # Publications
        if parsed_resume.get('publications'):
            sections.append("\nPUBLICATIONS:")
            for pub in parsed_resume['publications']:
                sections.append(f"- {pub}")
        
        return "\n".join(sections)
    
    def export_screening_to_json(
        self,
        screening_result: ResumeScreeningResult,
        file_path: str = None
    ) -> str:
        """Export screening result to JSON format."""
        json_data = screening_result.model_dump(exclude_none=True)
        json_string = json.dumps(json_data, indent=2, default=str)
        
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_string)
            logger.info(f"Screening result exported to: {file_path}")
        
        return json_string



