import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

try:
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents="Search Google and tell me the latest Python news.",
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )
    )

    print("SUCCESS:", response.text)

except Exception as e:
    print("FAILED:", e)