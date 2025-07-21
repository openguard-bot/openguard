import os
import litellm
from litellm import acompletion

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_GEMINI_MODEL = "gemini/gemini-2.5-flash-lite-preview-06-17"

async def generate_content(messages, model: str = DEFAULT_GEMINI_MODEL, **kwargs) -> str:
    """Generate text using Google's Gemini via LiteLLM."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    response = await acompletion(model=model, messages=messages, api_key=GEMINI_API_KEY, **kwargs)
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "message") and hasattr(choice.message, "content"):
            return choice.message.content
    return ""
