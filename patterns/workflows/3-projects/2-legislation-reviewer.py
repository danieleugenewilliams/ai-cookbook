from typing import List, Dict
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging
import dotenv

try:
    import tiktoken
except ImportError:
    raise ImportError(
        "The 'tiktoken' package is required. Install it with 'pip install tiktoken'."
    )


# Environment variables
dotenv.load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


client = OpenAI(api_key=api_key)
model = "gpt-4o"

# -----------------------------------------------------------
# Step 1: Define the data models
# -----------------------------------------------------------

"""Define the data models to describe the typical sections commonly found in U.S. legislation."""


class LegislationSection(BaseModel):
    """Represents a section of legislation."""

    section_number: str = Field(
        description="The number or identifier of the section (e.g., ‘Section 101’). Used for reference and citation."
    )
    title: str = Field(
        description="The title of the section, summarizing its content (e.g., ‘Short Title’). Provides context for the section."
    )
    content: str = Field(
        description="The text of the section, detailing its provisions and requirements. The main body of legislative text."
    )
    notes: str = Field(
        default=None,
        description="Additional notes or comments about the section, such as legislative history or interpretation guidance.",
    )
    uncommon_section: bool = Field(
        default=False,
        description="Indicates if the section is not commonly found in typical legislation. Useful for identifying unique or specialized provisions.",
    )


class LegislationLegalese(BaseModel):
    """Represents legal language used in legislation."""

    severability_clause: str = Field(
        default=None,
        description="A clause stating that if any part of the legislation is found invalid, the rest remains effective. Ensures the law's resilience.",
    )
    sunset_clause: str = Field(
        default=None,
        description="A provision that sets an expiration date for the legislation unless renewed. Used to limit the duration of certain laws.",
    )
    reporting_requirements: list[str] = Field(
        default=[],
        description="Mandates for reporting on the implementation or impact of the legislation. Ensures accountability and oversight.",
    )
    regulatory_authority: str = Field(
        default=None,
        description="Grants authority to a government agency to create regulations to implement the law. Defines the scope of regulatory power.",
    )
    enforcement_provisions: list[str] = Field(
        default=[],
        description="Details on how the law will be enforced, including penalties for non-compliance. Establishes the legal framework for enforcement actions.",
    )
    conforming_amendments: list[str] = Field(
        default=[],
        description="Amendments that adjust existing laws to align with the new legislation. Ensures consistency across legal texts.",
    )


class Legislation(BaseModel):
    """Represents a piece of legislation, such as a bill or act."""

    short_title: str = Field(
        description="Provides the official name of the act (e.g., “Patriot Act,” “Affordable Care Act”). Used for citation and public recognition."
    )
    table_of_contents: str = Field(
        description="Outlines the bill’s structure, listing titles, subtitles, and sections. Aids navigation in complex or lengthy bills."
    )
    findings_or_purpose: str = Field(
        description="States the rationale, problems addressed, or goals of the legislation. Establishes legislative intent for courts and agencies."
    )
    definitions: list[str] = Field(
        description="Defines key terms used in the bill to ensure clarity and consistency (e.g., “For purposes of this Act, ‘small business’ means…”)."
    )
    amendments: list[str] = Field(
        description="Lists changes to existing laws, specifying which sections are amended and how. Essential for understanding the bill’s impact on current law."
    )
    authorization_of_appropriations: str = Field(
        description="Allocates funding for programs or activities, often specifying amounts and fiscal years (e.g., “There is authorized to be appropriated $X for fiscal year Y”)."
    )
    effective_date: str = Field(
        description="Specifies when the law takes effect, which can be immediate, upon enactment, or at a later date. Important for implementation timelines."
    )
    sections: list[LegislationSection] = Field(
        description="Contains the main substantive provisions of the bill, detailing new laws or changes to existing laws."
    )
    legalese: LegislationLegalese = Field(
        default_factory=LegislationLegalese,
        description="Contains legal language and clauses that provide additional context or requirements for the legislation.",
    )


class LegislationValidation(BaseModel):
    """Validation results for the legislation analysis."""

    is_legislation: bool = Field(
        description="Indicates whether the input content is valid legislation and well-structured."
    )
    confidence_score: float = Field(
        description="Confidence score between 0 and 1 that the input content is a legislation document."
    )


# -----------------------------------------------------------
# Step 2: Define the parallel validation tasks
# -----------------------------------------------------------


def validate_legislation_content(
    legislation_text: str,
) -> LegislationValidation:
    """Validate if the input text is structured like legislation."""
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Determine if this text is structured like U.S. legislation.",
            },
            {
                "role": "user",
                "content": legislation_text,
            },
        ],
        response_format=LegislationValidation,
    )
    return completion.choices[0].message.parsed


def validate_legislation(legislation_text: str) -> bool:
    """Check if the legislation text is valid and well-structured."""
    logger.info("Validating legislation content...")

    validation = validate_legislation_content(legislation_text)

    is_valid = validation.is_legislation and validation.confidence_score >= 0.7

    if not is_valid:
        logger.warning(
            f"Validation failed: Legislation={validation.is_legislation}, Confidence={validation.confidence_score}"
        )

    logger.info(
        f"Validation successful: Legislation={validation.is_legislation}, Confidence={validation.confidence_score}"
    )
    return is_valid


# -----------------------------------------------------------
# Step 2: Define prompts
# -----------------------------------------------------------

ORCHESTRATOR_PROMPT = """
You are an expert in U.S. legislation drafting. Your task is to analyze a piece of legislation and identify its key sections, legal language, and any uncommon provisions.
Please provide a detailed analysis of the legislation, including:
1. A breakdown of the main sections, including their titles and content.
2. Any legalese or specialized language used, such as severability clauses, sunset clauses, or regulatory authority.
3. Identification of any uncommon sections that are not typically found in standard legislation.
4. A summary of the overall structure and purpose of the legislation.
Ensure your analysis is comprehensive and captures the nuances of the legislative text.
"""

# -----------------------------------------------------------
# Step 3: Implement the orchestrator
# -----------------------------------------------------------


class LegislationOrchestrator:
    """Orchestrator for analyzing legislation."""

    def __init__(self):
        self.legislation_content: str = {}

    def analyze_legislation(self, legislation_text: str) -> Legislation:
        """Analyze the provided legislation text and return a structured Legislation object."""
        logger.info("Start analyzing legislation content...")
        completions = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_PROMPT},
                {"role": "user", "content": legislation_text},
            ],
            response_format=Legislation,
        )
        logger.info("Finished analyzing legislation...")
        return completions.choices[0].message.parsed


# -----------------------------------------------------------
# Step 4: Example usage
# -----------------------------------------------------------


if __name__ == "__main__":
    print("Legislation Reviewer Workflow Example")

    orchestrator = LegislationOrchestrator()
    legislation_text = ""

    """Get approximately the first 50k tokens worth of content from legislation document"""

    # Load the document
    with open(
        "/Users/danielwilliams/Projects/ai-cookbook/patterns/workflows/3-projects/legislation.md",
        "r",
    ) as f:
        full_text = f.read()

    # Use tiktoken to count tokens (assuming OpenAI GPT-4 encoding)
    enc = tiktoken.encoding_for_model("gpt-4o")
    tokens = enc.encode(full_text)
    max_tokens = 4000

    # Truncate to the first 50k tokens and decode back to string
    truncated_text = enc.decode(tokens[:max_tokens])
    legislation_text = truncated_text
    legislation_object = {}
    if validate_legislation(legislation_text):
        legislation_object = orchestrator.analyze_legislation(legislation_text)
        print(
            f"Legislation Analysis Result:\n{legislation_object.model_dump_json(indent=2)}"
        )
