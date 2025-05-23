import json
import os
import dotenv

import requests
from openai import OpenAI
from pydantic import BaseModel, Field

dotenv.load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

"""
docs: https://platform.openai.com/docs/guides/function-calling
"""

# ------------------------------------------------
# Define the tool (function) that we want to call
# ------------------------------------------------


def get_weather(latitude, longitude):
    """
    This is a a publicly available API thhat returns the weather for a given location.
    """
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&timezone=America%2FNew_York&current=temperature_2m,apparent_temperature,relative_humidity_2m,is_day,precipitation#hourly_weather_variables"
    )
    data = response.json()
    return data["current"]


# test get_weather
# weather_data = get_weather(37.7749, -122.4194)  # San Francisco, CA
# print(json.dumps(weather_data, indent=2))

# ------------------------------------------------
# Step 1: Call the model with get_weather tool defined
# ------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

system_prompt = "You are a helpful weather assistant."

messages = [
    {"role": "system", "content": system_prompt},
    {
        "role": "user",
        "content": "What is the weather like in Paris today?",
    },
]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)

# ------------------------------------------------
# Step 2: Model decides to call function(s)
# ------------------------------------------------

completion.model_dump()

# ------------------------------------------------
# Step 3: Execute get_weather function
# ------------------------------------------------


def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)


for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
    )

# ------------------------------------------------
# Step 4: Supply result and call model again
# ------------------------------------------------


class WeatherResponse(BaseModel):
    temperature: float = Field(
        description="The current temperature in fahrenheit for the given location."
    )
    response: str = Field(
        description="A natural language response to the user's question."
    )


completion_2 = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    response_format=WeatherResponse,
)

# ------------------------------------------------
# Step 5: Check model response
# ------------------------------------------------

final_response = completion_2.choices[0].message.parsed
final_response.temperature
final_response.response
