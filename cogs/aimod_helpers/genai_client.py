from .litellm_config import (
    get_litellm_client,
    get_litellm_client_for_model,
)

__all__ = [
    "genai_client_us_central1",
    "genai_client_global",
    "genai_client",
    "get_genai_client_for_model",
]

# Initialize LiteLLM clients for backward compatibility
try:
    genai_client_us_central1 = get_litellm_client()
    genai_client_global = get_litellm_client()
    genai_client = genai_client_us_central1
    print("LiteLLM Clients initialized with OpenRouter backend.")
except Exception as e:
    genai_client_us_central1 = None
    genai_client_global = None
    genai_client = None
    print(f"Error initializing LiteLLM Clients: {e}")


def get_genai_client_for_model(model_name: str):
    """Return the appropriate LiteLLM client based on the model name."""
    return get_litellm_client_for_model(model_name)
