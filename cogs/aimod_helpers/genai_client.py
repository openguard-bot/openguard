import os
from google import genai

from .config_manager import VERTEX_PROJECT_ID, VERTEX_LOCATION

__all__ = [
    "genai_client_us_central1",
    "genai_client_global",
    "genai_client",
    "get_genai_client_for_model",
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    genai_client_us_central1 = genai.Client(
        vertexai=False,
        api_key=GEMINI_API_KEY,
    )
    genai_client_global = genai.Client(
        vertexai=False,
        api_key=GEMINI_API_KEY,
    )
    genai_client = genai_client_us_central1
    print("Google GenAI Clients initialized for us-central1 and global regions.")
except NameError:
    genai_client_us_central1 = None
    genai_client_global = None
    genai_client = None
    print("Google GenAI SDK (genai) not imported, skipping client initialization.")
except Exception as e:
    genai_client_us_central1 = None
    genai_client_global = None
    genai_client = None
    print(f"Error initializing Google GenAI Clients for Vertex AI: {e}")


def get_genai_client_for_model(model_name: str):
    """Return the appropriate genai client based on the model name."""
    if "gemini-2.5-pro" in model_name:
        return genai_client_global
    return genai_client_us_central1