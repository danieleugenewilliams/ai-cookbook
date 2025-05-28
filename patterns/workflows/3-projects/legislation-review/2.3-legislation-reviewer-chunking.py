from typing import List, Dict, Iterator
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging
import dotenv

import tiktoken
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

import time
from datetime import datetime, timedelta
from collections import deque


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

# Local LLM Setup
client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not-needed")
model = "gemma-3-4b-it-qat"

# OpenAI client setup
# client = OpenAI(api_key=api_key)
# model = "gpt-4o"

# Constants
# Maximum context length for the model
MAX_CONTEXT_LENGTH = 8000

# -----------------------------------------------------------
# Step 0: Define the rate limiter
# -----------------------------------------------------------
"""Rate limiter to control the number of requests to the OpenAI API."""


class RateLimiter:
    """Handles rate limiting for API requests."""

    def __init__(self, requests_per_minute: int = 50, max_retries: int = 5):
        self.requests_per_minute = requests_per_minute
        self.max_retries = max_retries
        self.request_timestamps = deque(maxlen=requests_per_minute)
        self.retry_intervals = [2, 4, 8, 16, 32]  # exponential backoff in seconds

    def wait_if_needed(self):
        """Check if we need to wait before making another request."""
        now = datetime.now()

        # Remove timestamps older than 1 minute
        while self.request_timestamps and self.request_timestamps[0] < now - timedelta(
            minutes=1
        ):
            self.request_timestamps.popleft()

        # If we've hit the rate limit, wait until we can make another request
        if len(self.request_timestamps) >= self.requests_per_minute:
            wait_time = (
                self.request_timestamps[0] + timedelta(minutes=1) - now
            ).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)

    def make_request_with_retry(self, request_func, *args, **kwargs):
        """Make a request with retry logic and rate limiting."""
        for retry in range(self.max_retries):
            try:
                self.wait_if_needed()
                result = request_func(*args, **kwargs)
                self.request_timestamps.append(datetime.now())
                return result
            except Exception as e:
                if "429" in str(e) or "RateLimitError" in str(e):
                    wait_time = self.retry_intervals[
                        min(retry, len(self.retry_intervals) - 1)
                    ]
                    logger.warning(
                        f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {retry + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                raise
        raise Exception(f"Failed after {self.max_retries} retries")


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


class TextChunker:
    """Handles chunking of large text documents into manageable pieces."""

    def __init__(self, chunk_size: int = None, overlap: int = 200):
        self.chunk_size = chunk_size or (
            MAX_CONTEXT_LENGTH // 2
        )  # Default to half the context length
        if self.chunk_size > MAX_CONTEXT_LENGTH:
            logger.warning(
                f"Chunk size {self.chunk_size} exceeds maximum context length. Adjusting..."
            )
            self.chunk_size = MAX_CONTEXT_LENGTH - 1000  # Leave room for system prompt
        self.overlap = min(
            overlap, self.chunk_size // 4
        )  # Ensure overlap isn't too large
        self.encoding = tiktoken.encoding_for_model("gpt-4o")

    def create_chunks(self, text: str) -> Iterator[tuple[str, int]]:
        """Split text into overlapping chunks, returning chunks with their position."""
        tokens = self.encoding.encode(text)

        logger.info(f"Total tokens in text: {len(tokens)}")
        if len(tokens) < self.chunk_size:
            logger.info("Text fits in single chunk")
            yield text, 0
            return

        start = 0
        logger.info("Creating text chunks...")
        while start < len(tokens):
            # Calculate end position
            end = start + min(self.chunk_size, len(tokens) - start)
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)

            # Find a good breaking point
            if len(chunk_text) > 100:
                last_period = chunk_text.rfind(". ")
                if last_period != -1:
                    chunk_text = chunk_text[: last_period + 1]
                    # Recalculate tokens for accurate positioning
                    chunk_tokens = self.encoding.encode(chunk_text)

            logger.info(f"Created chunk with {len(chunk_tokens)} tokens")
            yield chunk_text, start

            # Update start position
            next_start = start + len(chunk_tokens) - self.overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start
            logger.info(f"Next chunk will start at token index {start}...")
        logger.info("Finished creating text chunks.")


# -----------------------------------------------------------
# Step 2: Define the parallel validation tasks
# -----------------------------------------------------------


def validate_legislation_content(
    legislation_text: str,
) -> LegislationValidation:
    """Validate if the input text is structured like legislation."""
    rate_limiter = RateLimiter(requests_per_minute=50)

    return (
        rate_limiter.make_request_with_retry(
            client.beta.chat.completions.parse,
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
        .choices[0]
        .message.parsed
    )


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
        self.chunker = TextChunker(chunk_size=15000, overlap=200)
        self.legislation_content: Dict = {}
        self.rate_limiter = RateLimiter(requests_per_minute=50)

    def _make_api_request(self, chunk_text: str) -> Dict:
        """Make an API request with rate limiting."""
        # Count tokens in the prompt and content
        encoding = self.chunker.encoding
        system_tokens = len(encoding.encode(ORCHESTRATOR_PROMPT))
        content_tokens = len(encoding.encode(chunk_text))
        total_tokens = system_tokens + content_tokens

        if total_tokens > MAX_CONTEXT_LENGTH:
            logger.error(
                f"Total tokens ({total_tokens}) exceeds maximum context length"
            )
            raise ValueError(
                f"Input too large: {total_tokens} tokens (max {MAX_CONTEXT_LENGTH})"
            )

        logger.info(f"Making API request with {total_tokens} total tokens")
        return self.rate_limiter.make_request_with_retry(
            client.beta.chat.completions.parse,
            model=model,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_PROMPT},
                {"role": "user", "content": chunk_text},
            ],
            response_format=Legislation,
        )

    def analyze_chunk(self, chunk_data: tuple[str, int]) -> Dict:
        """Analyze a single chunk of legislation."""
        chunk_text, position = chunk_data
        logger.info(f"Analyzing chunk at position {position}...")

        completions = self._make_api_request(chunk_text)
        return {"position": position, "analysis": completions.choices[0].message.parsed}

    def analyze_legislation(self, legislation_text: str) -> Legislation:
        """Analyze the provided legislation text using chunking strategy."""
        logger.info("Start analyzing legislation content...")

        chunks = list(self.chunker.create_chunks(legislation_text))
        results = []
        failed_chunks = []

        # Process chunks in parallel with error handling
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.analyze_chunk, chunk) for chunk in chunks]

            for i, future in enumerate(tqdm(futures, desc="Analyzing chunks")):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Failed to process chunk {i}: {str(e)}")
                    failed_chunks.append(i)

        if failed_chunks:
            logger.warning(
                f"Failed to process {len(failed_chunks)} chunks: {failed_chunks}"
            )

        if not results:
            raise Exception("No chunks were successfully processed")

        # Merge results
        merged_legislation = self._merge_chunk_results(results)
        logger.info("Finished analyzing legislation...")
        return merged_legislation

    def _merge_chunk_results(self, results: List[Dict]) -> Legislation:
        """Merge the analysis results from multiple chunks."""
        logger.info("Started merging chunk results...")
        # Sort results by position
        sorted_results = sorted(results, key=lambda x: x["position"])

        # Initialize merged legislation
        merged = Legislation(
            short_title="",
            table_of_contents="",
            findings_or_purpose="",
            definitions=[],
            amendments=[],
            authorization_of_appropriations="",
            effective_date="",
            sections=[],
        )

        # Merge the results
        for result in sorted_results:
            analysis = result["analysis"]
            merged.sections.extend(analysis.sections)
            merged.definitions.extend(analysis.definitions)
            merged.amendments.extend(analysis.amendments)

            # Take the first non-empty value for single-value fields
            if not merged.short_title and analysis.short_title:
                merged.short_title = analysis.short_title
            if not merged.table_of_contents and analysis.table_of_contents:
                merged.table_of_contents = analysis.table_of_contents
            if not merged.findings_or_purpose and analysis.findings_or_purpose:
                merged.findings_or_purpose = analysis.findings_or_purpose
            if (
                not merged.authorization_of_appropriations
                and analysis.authorization_of_appropriations
            ):
                merged.authorization_of_appropriations = (
                    analysis.authorization_of_appropriations
                )
            if not merged.effective_date and analysis.effective_date:
                merged.effective_date = analysis.effective_date

        logger.info("Finished merging chunk results.")
        return merged


# -----------------------------------------------------------
# Step 4: Example usage
# -----------------------------------------------------------


if __name__ == "__main__":
    print("Legislation Reviewer Workflow Example")

    orchestrator = LegislationOrchestrator()

    # Load the document
    with open(
        "legislation.md",
        "r",
    ) as f:
        legislation_text = f.read()

    if validate_legislation(legislation_text[:4000]):  # Validate first chunk only
        legislation_object = orchestrator.analyze_legislation(legislation_text)
        result_json = legislation_object.model_dump_json(indent=2)
        print(f"Legislation Analysis Result:\n{result_json}")
        # Save to JSON file
        output_path = "legislation_analysis_result.json"
        with open(output_path, "w") as outfile:
            outfile.write(result_json)
        print(f"Analysis result saved to {output_path}")
