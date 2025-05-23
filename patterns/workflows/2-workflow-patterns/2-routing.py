from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging
import dotenv

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
# Step 1: Define the data model for routing and requests
# -----------------------------------------------------------


class CalendarRequestType(BaseModel):
    """Router LLM call: Determine the type of calendar request."""

    request_type: Literal["new_event", "modify_event", "other"] = Field(
        description="Type of calendar requestbeing made."
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1.")
    description: str = Field("Cleaned description of the request.")


class NewEventDetails(BaseModel):
    """RDetails for creating a new event."""

    name: str = Field(description="Name of the event.")
    date: str = Field(description="Date of the event (ISO 8601 format).")
    duration_minutes: int = Field(description="Duration of the event in minutes.")
    participants: List[str] = Field(description="List of participants for the event.")


class Change(BaseModel):
    """Details for changing an existing event."""

    field: str = Field(description="Field to change.")
    new_value: str = Field(description="New value for the field.")


class ModifyEventDetails(BaseModel):
    """Details for modifying an existing event."""

    event_identifier: str = Field(description="Description to identify the event.")
    changes: List[Change] = Field(description="List of changes to apply to the event.")
    participants_to_add: List[str] = Field(description="List of participants to add.")
    participants_to_remove: List[str] = Field(
        description="List of participants to remove."
    )


class CalendarResponse(BaseModel):
    """Final response format."""

    status: bool = Field(description="Whether the operation was successful.")
    message: str = Field(
        description="User-friendly message to be displayed to the user."
    )
    calendar_link: Optional[str] = Field(
        description="Link to the calendar event, if applicable."
    )


# -----------------------------------------------------------
# Step 2: Define the routing and processing functions
# -----------------------------------------------------------


def route_calendar_request(user_input: str) -> CalendarRequestType:
    """Router LLM call to determine the type of calendar request."""

    # Call the LLM to determine the type of request
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Determine if this is a request to create a new calendar event or modify an existing one.",
            },
            {"role": "user", "content": user_input},
        ],
        response_format=CalendarRequestType,
    )
    result = completion.choices[0].message.parsed
    logger.info(
        f"Request routed as: {result.request_type} with confidence {result.confidence_score}"
    )
    return result


def handle_new_event(description: str) -> CalendarResponse:
    """Handle the creation of a new calendar event."""

    # Simulate creating a new event
    logger.info(f"Creating new event: {description}")

    # Get event details
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Extract details for creating a new calendar event.",
            },
            {"role": "user", "content": description},
        ],
        response_format=NewEventDetails,
    )
    details = completion.choices[0].message.parsed

    logger.info(f"New Event: {details.model_dump()}")

    # Generate response
    return CalendarResponse(
        status=True,
        message=f"New event '{details.name}' for {details.date} created successfully.",
        calendar_link=f"calendar://new?event={details.name}",
    )


def handle_modify_event(description: str) -> CalendarResponse:
    """Handle the modification of an existing calendar event."""

    # Simulate modifying an existing event
    logger.info("Processing event modification request")

    # Get event details
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Extract details for modifying an existing calendar event.",
            },
            {"role": "user", "content": description},
        ],
        response_format=ModifyEventDetails,
    )
    details = completion.choices[0].message.parsed

    logger.info(f"Modified Event: {details.model_dump()}")

    # Generate response
    return CalendarResponse(
        status=True,
        message=f"Event '{details.event_identifier}' modified successfully.",
        calendar_link=f"calendar://modify?event={details.event_identifier}",
    )


def process_calendar_request(user_input: str) -> CalendarResponse:
    """Main function implementing the routing workflow."""

    # Route the request
    route_result = route_calendar_request(user_input)

    # Check confidence threshold
    if route_result.confidence_score < 0.7:
        logger.warning(f"Low confidence score: {route_result.confidence_score}")
        return None

    # Route to the appropriate handler
    if route_result.request_type == "new_event":
        return handle_new_event(route_result.description)
    elif route_result.request_type == "modify_event":
        return handle_modify_event(route_result.description)
    else:
        logger.error("Request type not supported.")
        return None


# -----------------------------------------------------------
# Step 3: Test with new event
# -----------------------------------------------------------

new_event_input = "Let's schedule a team meeting next Tuesday at 2 PM for 1 hour with Alice, Bob, Greg, and Lana."
result = process_calendar_request(new_event_input)
if result:
    print(f"Response: {result.message}")

# -----------------------------------------------------------
# Step 4: Test with modify event
# -----------------------------------------------------------
modify_event_input = "Change the meeting with Alice and Bob to next Wednesday at 3 PM."
result = process_calendar_request(modify_event_input)
if result:
    print(f"Response: {result.message}")

# -----------------------------------------------------------
# Step 5: Test with unsupported request
# -----------------------------------------------------------
invalid_input = "What is the weather like today?"
result = process_calendar_request(invalid_input)
if result:
    print(f"Response: {result.message}")
