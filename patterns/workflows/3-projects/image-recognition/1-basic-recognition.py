# patterns/workflows/3-projects/image-recognition/1-basic-recognition.py
"""Send an image to the LLM and get a description of the image."""

import os
import logging
import dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from PIL import Image
from io import BytesIO
import argparse

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
client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key=api_key)
model = "gemma-3-4b-it-qat"

# --------------------------------------------------------------------------
# Step 1: Define the Data Models
# --------------------------------------------------------------------------


class ImageDescriptionRequest(BaseModel):
    """Request model for image description."""

    image: str = Field(..., description="Base64 encoded image string")


class ImageDescriptionResponse(BaseModel):
    """Response model for image description."""

    description: str = Field(..., description="Description of the image")


# --------------------------------------------------------------------------
# Step 2: Define the Function to Describe the Image
# --------------------------------------------------------------------------


def describe_image(image_path: str) -> ImageDescriptionResponse:
    """Describe the image using the LLM."""
    try:
        # Load the image
        try:
            image = Image.open(image_path)
        except Exception:
            raise ValueError("Image could not be loaded.")

        # Convert the image to bytes
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        image_bytes = buffered.getvalue()

        # Encode the image to base64
        import base64

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        logger.info("Image loaded and encoded successfully.")
        logger.info(f"Image size: {len(encoded_image)} bytes")

        # Prepare the OpenAI-compatible vision message format
        messages = [
            {"role": "system", "content": "You are an expert in describing images."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                    },
                ],
            },
        ]

        # Call the LLM to get the description
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        # Use attribute access for message content
        description = response.choices[0].message.content

        return ImageDescriptionResponse(description=description)

    except Exception as e:
        logger.error(f"Error describing image: {e}")
        raise e


# --------------------------------------------------------------------------
# Step 3: Example Usage with Command-Line Arguments
# --------------------------------------------------------------------------


def main(input_file: str, output_file: str):
    try:
        # Describe the image
        description_response = describe_image(input_file)
        print(f"Image Description: {description_response.description}")

        with open(output_file, "w") as f:
            f.write(f"# Image Description\n\n{description_response.description}\n")
        logger.info(f"Description saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to describe image: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send an image to the LLM and get a description of the image."
    )
    parser.add_argument("input_file", type=str, help="Path to the input image file")
    parser.add_argument(
        "output_file", type=str, help="Path to the output markdown file"
    )

    args = parser.parse_args()

    main(args.input_file, args.output_file)
