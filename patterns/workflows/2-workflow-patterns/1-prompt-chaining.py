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

# -----------------------------------------------------------
# Step 1: Define the data models for each stage
# -----------------------------------------------------------


class EventExtraction(BaseModel):
    """First LLM call: Extract basic event information."""

    description: str = Field(..., description="Raw description of the event")
    is_calendar_event: bool = Field(description="Whether this is a calendar event")
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class EventDetails(BaseModel):
    """Second LLM call: Parse specific event details."""

    name: str = Field(description="Name of the event")
    date: str = Field(description="Date of the event. Use ISO 8601 format")
    duration_minutes: int = Field(
        description="Expected duration of the event in minutes"
    )
    participants: list[str] = Field(description="List of participants in the event")
    location: Optional[str] = Field(description="Location of the event")


class EventConfirmation(BaseModel):
    """Third LLM call: Generate confirmation message."""

    confirmation_message: str = Field(
        description="Natural language confirmation message"
    )
    calendar_link: Optional[str] = Field(
        description="Generated calendar link to the event, if applicable"
    )


# -----------------------------------------------------------
# Step 2: Define the functions
# -----------------------------------------------------------


def extract_event_info(user_input: str) -> EventExtraction:
    """First LLM call to determine if input is a calender event."""
    logger.info("Extracting event information...")
    logger.debug(f"User info: {user_input}")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}"

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"{date_context} Analyze if the text description is a calendar event.",
            },
            {
                "role": "user",
                "content": user_input,
            },
        ],
        response_format=EventExtraction,
    )
    result = completion.choices[0].message.parsed
    logger.info(f"Extraction complete - Is calendar event: {result.is_calendar_event}")
    return result


def parse_event_details(description: str) -> EventDetails:
    """Second LLM call to parse event details."""
    logger.info("Parsing event details parsing...")
    logger.debug(f"Event description: {description}")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}"

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Extract specific details from the event description.",
            },
            {
                "role": "user",
                "content": description,
            },
        ],
        response_format=EventDetails,
    )
    result = completion.choices[0].message.parsed
    logger.info(
        f"Parsed event details - Name: {result.name}, Date: {result.date}, Duration: {result.duration_minutes} minutes, Participants: {result.participants}, Location: {result.location}"
    )
    return result


def generate_confirmation(event_details: EventDetails) -> EventConfirmation:
    """Third LLM call to generate a confirmation message."""
    logger.info("Generating confirmation message...")

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Generate a natural confirmation message for the event. Sign of with your name Pete",
            },
            {
                "role": "user",
                "content": str(event_details.model_dump()),
            },
        ],
        response_format=EventConfirmation,
    )
    result = completion.choices[0].message.parsed
    logger.info("Confirmation message generated.")
    return result


# -----------------------------------------------------------
# Step 3: Chain the functions together
# -----------------------------------------------------------


def process_calendar_event(user_input: str) -> EventConfirmation:
    """Main function implementing the prompt chain with gate check."""
    logger.info("Processing calendar event...")
    logger.debug(f"URaw input: {user_input}")

    # First LLM call to extract basic info
    initial_extraction = extract_event_info(user_input)

    if (
        not initial_extraction.is_calendar_event
        or initial_extraction.confidence_score < 0.7
    ):
        logger.warning(
            f"Gate checked failed - is_calendar_event: {initial_extraction.is_calendar_event}, confidence_score: {initial_extraction.confidence_score}"
        )
        return None

    logger.info("Gate check passed - Proceeding to parse event details...")

    # Second LLM call to parse event details
    event_details = parse_event_details(initial_extraction.description)

    # Third LLM call to generate confirmation message
    confirmation = generate_confirmation(event_details)

    logger.info("Event processing completed successfully.")
    return confirmation


# -----------------------------------------------------------
# Step 4: Test the chain (workflow) with a valid input
# -----------------------------------------------------------

user_input = "Let's schedule a 1h meeting with John and Sarah on next Friday at 3 PM to discuss the new project roadmap at HQ in the main conference room."

result = process_calendar_event(user_input)
if result:
    logger.info(f"Confirmation message: {result.confirmation_message}")
    if result.calendar_link:
        logger.info(f"Calendar link: {result.calendar_link}")
else:
    print("This doesn't appear to be a calendar event request.")

# -----------------------------------------------------------
# Step 5: Test the chain (workflow) with an invalid input
# -----------------------------------------------------------
user_input = "Can you send an email to Alice and Bob to discuss the project updates?"

result = process_calendar_event(user_input)
if result:
    print(f"Confirmation message: {result.confirmation_message}")
    if result.calendar_link:
        print(f"Calendar link: {result.calendar_link}")
else:
    print("This doesn't appear to be a calendar event request.")
