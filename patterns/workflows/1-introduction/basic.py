import os
import dotenv

from openai import OpenAI

dotenv.load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
# print(api_key)

client = OpenAI(api_key=api_key)

try:
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Write a limerick about the Python programming language.",
            },
        ],
    )

    response = completion.choices[0].message.content
    print(response)
except Exception as e:
    print(f"An error occurred: {e}")
