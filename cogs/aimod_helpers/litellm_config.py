"""
LiteLLM configuration module for OpenRouter integration.
This module handles the setup and configuration of LiteLLM with OpenRouter as the backend provider.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
import litellm
from litellm import acompletion

# Configure LiteLLM settings
litellm.set_verbose = False  # Set to True for debugging
litellm.drop_params = True  # Drop unsupported parameters instead of erroring

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("SLIPSTREAM_OPENROUTER_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model mappings from Google models to OpenRouter equivalents
MODEL_MAPPINGS = {
    # Gemini models are no longer mapped to prevent automatic "openrouter/" prepending.
    # Users should provide the full model name, e.g., "openrouter/google/gemini-2.5-pro".
    # "gemini-2.5-flash-lite": "openrouter/google/gemini-2.5-flash-lite-preview-06-17",
    # "gemini-2.5-flash": "openrouter/google/gemini-2.5-flash",
    # "gemini-2.5-pro": "openrouter/google/gemini-2.5-pro",
    # Default fallback models
    "default": "github_copilot/gpt-4.1",
    "fallback": "github_copilot/gpt-4o",
}

# Default model configuration
DEFAULT_MODEL = "github_copilot/gpt-4.1"
FALLBACK_MODEL = "github_copilot/gpt-4o"

# Standard generation parameters for OpenRouter
DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.2,
    "max_tokens": 4096,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
}


class LiteLLMClient:
    """
    A wrapper class for LiteLLM that provides a consistent interface
    similar to the original Google GenAI client.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LiteLLM client.

        Args:
            api_key: OpenRouter API key. If None, will use environment variable.
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Please set SLIPSTREAM_OPENROUTER_KEY environment variable."
            )

        # Configure LiteLLM for OpenRouter
        os.environ["OPENROUTER_API_KEY"] = self.api_key

        print("LiteLLM client initialized with OpenRouter backend.")

    def map_model_name(self, model_name: str) -> str:
        """
        Returns the model name to be used with LiteLLM.
        If a model name is not in MODEL_MAPPINGS, it is returned as is,
        which allows passing custom model names directly.

        Args:
            model_name: The model name to use.

        Returns:
            The model name for the API call, or a default if model_name is empty.
        """
        if not model_name:
            return MODEL_MAPPINGS.get("default", DEFAULT_MODEL)

        # If a mapping exists, use it. Otherwise, use the name as is.
        # This ensures model names are shown "exactly as is" without modification.
        return MODEL_MAPPINGS.get(model_name, model_name)

    async def generate_content(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        auth_info: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Generate content using LiteLLM with OpenRouter.

        Args:
            model: Model name to use
            messages: List of message dictionaries
            api_key: User-provided API key (optional)
            auth_info: Additional authentication info (e.g., for GitHub Copilot)
            **kwargs: Additional generation parameters

        Returns:
            Response object with generated content
        """
        # Get the final model name, using the provided name as-is if not mapped.
        final_model_name = self.map_model_name(model)

        # Prepare generation config
        generation_config = DEFAULT_GENERATION_CONFIG.copy()
        generation_config.update(kwargs)

        # Determine the API key to use
        final_api_key = api_key or self.api_key

        # Prepare extra headers
        extra_headers = {
            "editor-version": "vscode/1.85.1",
            "Copilot-Integration-Id": "vscode-chat",
        }

        try:
            # Make the API call using LiteLLM
            response = await acompletion(
                model=final_model_name,
                messages=messages,
                api_key=final_api_key,
                extra_headers=extra_headers,
                auth=auth_info,  # Pass auth_info directly
                **generation_config,
            )

            # Wrap response to match expected interface
            return LiteLLMResponse(response)

        except Exception as e:
            print(f"Error calling API with model {final_model_name}: {e}")

            # Try fallback model if the primary model fails
            if final_model_name != FALLBACK_MODEL:
                print(f"Retrying with fallback model: {FALLBACK_MODEL}")
                try:
                    response = await acompletion(
                        model=FALLBACK_MODEL,
                        messages=messages,
                        api_key=self.api_key,  # Use default key for fallback
                        extra_headers={
                            "editor-version": "vscode/1.85.1",
                            "Copilot-Integration-Id": "vscode-chat",
                        },
                        auth=auth_info,
                        **generation_config,
                    )
                    return LiteLLMResponse(response)
                except Exception as fallback_error:
                    print(f"Fallback model also failed: {fallback_error}")

            raise e


class LiteLLMResponse:
    """
    A wrapper class for LiteLLM responses to match the expected interface
    from the original Google GenAI client.
    """

    def __init__(self, response):
        """
        Initialize the response wrapper.

        Args:
            response: Raw LiteLLM response object
        """
        self._response = response

    @property
    def text(self) -> str:
        """
        Extract text content from the response.

        Returns:
            Generated text content
        """
        try:
            if hasattr(self._response, "choices") and self._response.choices:
                choice = self._response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    return choice.message.content or ""
            return ""
        except Exception as e:
            print(f"Error extracting text from response: {e}")
            return ""

    @property
    def usage(self) -> Optional[Dict[str, Any]]:
        """
        Get usage information from the response.

        Returns:
            Usage information dictionary or None
        """
        try:
            if hasattr(self._response, "usage"):
                return {
                    "prompt_tokens": getattr(self._response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(
                        self._response.usage, "completion_tokens", 0
                    ),
                    "total_tokens": getattr(self._response.usage, "total_tokens", 0),
                }
        except Exception:
            pass
        return None


# Global client instances
_litellm_client = None
_litellm_client_global = None


def get_litellm_client() -> LiteLLMClient:
    """
    Get or create the global LiteLLM client instance.

    Returns:
        LiteLLMClient instance
    """
    global _litellm_client
    if _litellm_client is None:
        _litellm_client = LiteLLMClient()
    return _litellm_client


def get_litellm_client_for_model(model_name: str) -> LiteLLMClient:
    """
    Get the appropriate LiteLLM client for a given model.
    For now, all models use the same client, but this maintains
    compatibility with the original interface.

    Args:
        model_name: Name of the model

    Returns:
        LiteLLMClient instance
    """
    return get_litellm_client()


# Compatibility aliases
litellm_client = get_litellm_client()
litellm_client_us_central1 = get_litellm_client()
litellm_client_global = get_litellm_client()
