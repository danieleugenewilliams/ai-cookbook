from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=api_key)
model = "gpt-4o"

"""This project analyzes job requirements to extract key information from job descriptions.
It identifies required qualifications, responsibilities, and skills to help candidates understand job expectations.
It then analyzes the job requirements to provide a preliminary score, final score, and a detailed analysis of 
how reslient the job is to automation and AI.
This can be used by job seekers to assess their fit for a position and by employers to refine job postings.
"""


# -----------------------------------------------------------
# Step 1: Define the data models for job requirements analysis
# -----------------------------------------------------------
class JobDescription(BaseModel):
    """Represents a job description."""

    title: str = Field(..., description="Job title")

    description: str = Field(..., description="Detailed job description")

    experience_qualifications: list[str] = Field(
        default_factory=list, description="List of required experience qualifications"
    )

    responsibilities_or_tasks: list[str] = Field(
        default_factory=list, description="List of job responsibilities or tasks"
    )

    education_qualifications: Optional[list[str]] = Field(
        default_factory=list, description="List of required education qualifications"
    )

    certifications: Optional[list[str]] = Field(
        default_factory=list, description="List of required certifications"
    )

    skills: Optional[list[str]] = Field(
        default_factory=list, description="Required skills"
    )

    location: Optional[str] = Field(
        default=None, description="Job location (if applicable)"
    )

    employment_type: Optional[str] = Field(
        default=None, description="Type of employment (e.g., full-time, part-time)"
    )


class JobAnalysis(BaseModel):
    """Represents the analysis of a job description."""

    job_description: JobDescription = Field(
        ..., description="Job description to analyze"
    )

    preliminary_score: float = Field(
        default=0.0,
        description="Preliminary score based on an initial reading of the job requirements",
    )

    final_score: float = Field(
        default=0.0,
        description="Final score after a more detailed analysis of the job requirements",
    )

    reslience_level: str = Field(
        default="",
        description="Resilience level based on the score, e.g., Highly Resilient, Resilient, Moderately Resilient, Vulnerable, Highly Vulnerable",
    )

    automation_resilience_analysis: str = Field(
        default="",
        description="Analysis of how resilient the job is to automation and AI",
    )

    recommendations_to_improve_resilience: list[str] = Field(
        default=None,
        description="Recommendations to improve the job's resilience to automation and AI",
    )


class JobAnalysisSummary(BaseModel):
    """Represents a summary of the job analysis."""

    job_title: str = Field(..., description="Title of the job")

    preliminary_score: float = Field(
        default=0.0, description="Preliminary score based on initial analysis"
    )

    final_score: float = Field(
        default=0.0, description="Final score after detailed analysis"
    )

    resilience_level: str = Field(
        default="", description="Resilience level based on the final score"
    )

    automation_resilience_analysis: str = Field(
        default="", description="Detailed analysis of automation resilience"
    )

    recommendations_to_improve_resilience: Optional[list[str]] = Field(
        default=None,
        description="Recommendations to improve the job's resilience to automation and AI",
    )

    natural_language_analysis: Optional[str] = Field(
        default=None,
        description="Natural language summary of the job analysis, starting with the resilience level, preliminary score, final score, and recommendations, then followed by an explanation of the resilence level, final score, preliminary score, and the implications on the human in the role.",
    )


# -----------------------------------------------------------
# Step 2: Define the functions for job requirements analysis
# -----------------------------------------------------------


def get_job_description(job_description_text: str) -> JobDescription:
    """Retrieve a sample job description for analysis."""
    logger.info("Retrieving job description...")

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Provide a sample job description for analysis.",
            },
            {
                "role": "user",
                "content": job_description_text,
            },
        ],
        response_format=JobDescription,
    )
    return completion.choices[0].message.parsed


def analyze_automation_resilience(job_description: JobDescription) -> JobAnalysis:
    """Analyze how resilient the job is to automation and AI."""
    logger.info("Analyzing automation resilience...")

    resilience_prompt = """
You are an AI model trained to evaluate job descriptions using the Workforce Automation Resiliency Evaluation (WARE) framework. The WARE framework is used to assess the potential for automation of tasks within a job description and to provide qualitative and quantitative scores. All scores (Preliminary and Final) must be normalized to a range of 0–100. Ensure the Preliminary Score represents the raw automation resilience and the Final Score reflects adjustments for contextual factors like human qualities, physical requirements, or environmental challenges. 

Analyze how resilient the job is to automation and AI. Provide a detailed analysis that includes a preliminary_score based on the text provided. Analyze the structured data provided in the job description.
The analysis should include:
    - A preliminary score based on the job description text.
    - A final score after a more detailed analysis of the job requirements.
    - A detailed analysis of how resilient the job is to automation and AI.
The analysis should consider the following factors:
    - The nature of the tasks involved in the job.
    - The level of human interaction required.
    - The degree of creativity and decision-making involved.
    - The potential for automation of routine tasks.
The analysis should also include a breakdown of the score based on the following criteria:
    - Human Interaction: The extent to which the job requires human interaction

Determine the resilience level based on the score
Range	Level	                Designation	        Description
90–100	Highly Resilient	    Human-Centered	    The job is deeply rooted in human qualities like creativity, empathy, and decision-making, with minimal automation risk.
75–89	Resilient	            Tech-Integrated	    The job balances human-centered tasks with technology integration, making it resilient but adaptable to automation tools.
50–74	Moderately Resilient	Hybrid Potential	A mix of tasks: some are resistant to automation while others are routine and can be automated with emerging technologies.
25–49	Vulnerable	            Automation-Prone	The job includes significant portions of repetitive or predictable tasks that are highly automatable with current tools.
0–24	Highly Vulnerable	    Fully Automatable	The job consists primarily of tasks that can be fully automated, with little to no human intervention required.

Please follow these steps to evaluate a job description and return the output in JSON format:

Steps for Analysis:
                                          
    1. **Task Categorization**: Break down the job description into individual tasks or responsibilities. For each task, categorize its potential for automation:
        - Category A: High potential for automation. These tasks are repetitive, predictable, or can be performed by current technology, such as data entry, basic calculations, or routine analysis.
        - Category B: Low potential for automation. These tasks require human skills like creativity, empathy, decision-making in uncertain conditions, or complex problem-solving.
                                          
    2. **Weight Assignment**: Assign a weight to each task to reflect its importance to the overall role:
        - High Weight: Tasks with a greater weight (e.g., 15-20) are central to the role and may have a greater impact on the overall automation score.
        - Low Weight: Tasks with lower weights (e.g., 10 or less) are less central to the role or less significant in determining the role’s automation potential.
                                          
    3. **Score Calculation**: Calculate the Preliminary Score as follows:
        - Sum the weights of all tasks in Category A (i.e., tasks with high automation potential).
        - Adjust the preliminary score based on factors like the need for human qualities (e.g., empathy, leadership) and physical requirements or work in unpredictable environments.
        - The Final Score is an adjusted score that accounts for factors that affect the likelihood of automation. It considers not only the automation potential of individual tasks but also the context in which these tasks are performed, as well as any mitigating factors such as the need for human qualities, safety requirements, and physical/manual tasks.
        - Calculate the Final WARE Score on a scale from 0 to 100:
            - 0 means fully automatable.
            - 100 means highly resilient to automation.
        - Provide reasoning for adjustments made to the preliminary score to derive the final score.
        - Provide recommendations to improve the automation resiliency and human-centeredness of the job

    4. **Output Format**: Return the analysis in JSON format with the following fields:
        - job_description: The original job description text.
        - preliminary_score: The preliminary score based on the initial reading of the job requirements.
        - final_score: The final score after a more detailed analysis of the job requirements.
        - reslience_level: The resilience level based on the final score, e.g., Highly Resilient, Resilient, Moderately Resilient, Vulnerable, Highly Vulnerable.
        - automation_resilience_analysis: A detailed analysis of how resilient the job is to automation and AI.
        - recommendations_to_improve_resilience: A list of recommendations to improve the job's resilience to automation and AI.
    """

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": resilience_prompt,
            },
            {
                "role": "user",
                "content": job_description.model_dump_json(indent=2),
            },
        ],
        response_format=JobAnalysis,
    )
    return completion.choices[0].message.parsed


def natural_language_analysis(job_analysis: JobAnalysis) -> JobAnalysisSummary:
    """Perform a natural language analysis of the job description."""
    logger.info("Performing natural language analysis...")

    analysis_prompt = """
    Review the job analysis and provide a detailed natural language overview.
    The analysis should include:
        - A summary of the job requirements.
        - Key skills and qualifications required.
        - Potential challenges and opportunities in the role.
        - User-friendly language that can be easily understood by job seekers and employers.
    """

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": analysis_prompt,
            },
            {
                "role": "user",
                "content": f"Job Analysis: {job_analysis.model_dump_json(indent=2)}",
            },
        ],
        response_format=JobAnalysisSummary,
    )
    return completion.choices[0].message.parsed


# Example usage
if __name__ == "__main__":
    logger.info("Starting job requirements analysis workflow...")
    # Load the document

    # job_path = "paralegal.md"

    # job_path = "assistant-general-counsel.md"

    # job_path = "electrician.md"

    # job_path = "cybersecurity.md"

    job_path = "softwareengineer.md"

    job_desc_text = ""
    with open(
        job_path,
        "r",
    ) as f:
        job_desc_text = f.read()

    job_desc = get_job_description(job_desc_text)

    automation_resilience = analyze_automation_resilience(job_desc)

    natural_language_analysis_result = natural_language_analysis(automation_resilience)

    print("Automation Resilience Analysis Result:")
    print(f"{automation_resilience.model_dump_json(indent=2)}")

    print("Natural Language Analysis Result:")
    print(natural_language_analysis_result)
    logger.info("Job requirements analysis completed successfully.")
