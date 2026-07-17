import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemma-4-26b-a4b-it"

with open("system_instruction.txt", "r", encoding="utf-8") as f:
    SYSTEM_INSTRUCTION = f.read()

CONFIG = types.GenerateContentConfig(
    system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
    temperature=0.3,
)

def get_tutor_response(student_message: str, language: str) -> dict:
    """Send a message to the tutor and return the parsed JSON as a dict."""
    full_message = f"[TARGET_LANGUAGE: {language}]\n\n{student_message}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_message)],
            ),
        ],
        config=CONFIG,
    )
    raw = (response.text or "").strip()

    # Small models sometimes wrap JSON in markdown fences — strip them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "mode": "error",
            "raw_output": raw,
            "message": "The tutor's response was not valid JSON.",
        }