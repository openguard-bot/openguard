#!/usr/bin/env python3
"""
Test script to verify LiteLLM integration with OpenRouter.
This script tests the basic functionality of the refactored LLM code.
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(".env")


async def test_litellm_config():
    """Test the LiteLLM configuration module."""
    print("Testing LiteLLM configuration...")

    try:
        from cogs.aimod_helpers.litellm_config import (
            get_litellm_client,
            MODEL_MAPPINGS,
            DEFAULT_MODEL,
            LiteLLMClient,
        )

        print("✓ Successfully imported LiteLLM configuration")
        print(f"✓ Default model: {DEFAULT_MODEL}")
        print(f"✓ Available model mappings: {len(MODEL_MAPPINGS)} models")

        # Test client initialization
        client = get_litellm_client()
        print("✓ LiteLLM client initialized successfully")

        # Test model mapping
        test_models = ["gemini-2.5-flash", "gemini-2.5-pro", "unknown-model"]
        for model in test_models:
            mapped = client.map_model_name(model)
            print(f"✓ Model mapping: {model} -> {mapped}")

        return True

    except Exception as e:
        print(f"✗ Error testing LiteLLM configuration: {e}")
        return False


async def test_genai_client():
    """Test the refactored genai_client module."""
    print("\nTesting genai_client module...")

    try:
        from cogs.aimod_helpers.genai_client import (
            genai_client,
            genai_client_us_central1,
            genai_client_global,
            get_genai_client_for_model,
        )

        print("✓ Successfully imported genai_client")
        print(f"✓ Main client available: {genai_client is not None}")
        print(f"✓ US Central client available: {genai_client_us_central1 is not None}")
        print(f"✓ Global client available: {genai_client_global is not None}")

        # Test client retrieval for different models
        test_models = ["gemini-2.5-flash", "gemini-2.5-pro"]
        for model in test_models:
            client = get_genai_client_for_model(model)
            print(f"✓ Got client for model {model}: {client is not None}")

        return True

    except Exception as e:
        print(f"✗ Error testing genai_client: {e}")
        return False


async def test_config_manager():
    """Test the updated config_manager module."""
    print("\nTesting config_manager module...")

    try:
        from cogs.aimod_helpers.config_manager import (
            DEFAULT_AI_MODEL,
            DEFAULT_VERTEX_AI_MODEL,
            VERTEX_PROJECT_ID,
            VERTEX_LOCATION,
        )

        print("✓ Successfully imported config_manager")
        print(f"✓ Default AI model: {DEFAULT_AI_MODEL}")
        print(f"✓ Default Vertex AI model (legacy): {DEFAULT_VERTEX_AI_MODEL}")
        print(f"✓ Vertex project ID: {VERTEX_PROJECT_ID}")
        print(f"✓ Vertex location: {VERTEX_LOCATION}")

        return True

    except Exception as e:
        print(f"✗ Error testing config_manager: {e}")
        return False


async def test_api_call():
    """Test an actual API call to OpenRouter via LiteLLM."""
    print("\nTesting actual API call...")

    try:
        from cogs.aimod_helpers.litellm_config import get_litellm_client

        client = get_litellm_client()

        # Simple test message
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Respond with a simple JSON object containing a 'message' field.",
            },
            {"role": "user", "content": "Say hello in JSON format."},
        ]

        print("Making API call to OpenRouter...")
        response = await client.generate_content(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages,
            temperature=0.1,
            max_tokens=1000,
        )

        response_text = response.text
        print(f"✓ API call successful")
        print(f"✓ Response length: {len(response_text)} characters")
        print(f"✓ Response preview: {response_text[:200]}...")

        # Try to parse as JSON
        try:
            if "{" in response_text:
                json_start = response_text.find("{")
                json_text = response_text[json_start:].strip()
                if json_text.endswith("```"):
                    json_text = json_text[:-3]
                parsed = json.loads(json_text)
                print(f"✓ Response contains valid JSON: {parsed}")
        except:
            print("! Response is not JSON (this is okay for this test)")

        return True

    except Exception as e:
        print(f"✗ Error testing API call: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_moderation_simulation():
    """Test a simulated moderation scenario."""
    print("\nTesting moderation simulation...")

    try:
        from cogs.aimod_helpers.litellm_config import get_litellm_client
        from cogs.aimod_helpers.system_prompt import SYSTEM_PROMPT_TEMPLATE

        client = get_litellm_client()

        # Simulate a moderation request
        rules_text = """
        1. No spam or excessive posting
        2. Be respectful to other members
        3. No NSFW content in general channels
        4. No harassment or bullying
        5. Follow Discord Terms of Service
        """

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(rules_text=rules_text)

        user_prompt = """
**Context Information:**
- User's Server Role: Member
- Channel Category: General
- Channel Age-Restricted/NSFW (Discord Setting): False
- Recent Channel History:
User1: How's everyone doing today?
User2: Pretty good, just working on some code

**User's Infraction History:**
No previous infractions.

**Message Content:**
Hello everyone! Hope you're all having a great day!
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print("Testing moderation scenario...")
        response = await client.generate_content(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )

        response_text = response.text
        print(f"✓ Moderation API call successful")
        print(f"✓ Response length: {len(response_text)} characters")

        # Try to extract JSON
        try:
            json_start = response_text.find("{")
            if json_start != -1:
                json_text = response_text[json_start:].strip()
                if json_text.startswith("```json"):
                    json_text = json_text[7:]
                if json_text.endswith("```"):
                    json_text = json_text[:-3]
                json_text = json_text.strip()

                decision = json.loads(json_text)
                required_keys = ["reasoning", "violation", "rule_violated", "action"]

                if all(key in decision for key in required_keys):
                    print(f"✓ Valid moderation decision received:")
                    print(f"  - Violation: {decision['violation']}")
                    print(f"  - Rule: {decision['rule_violated']}")
                    print(f"  - Action: {decision['action']}")
                    print(f"  - Reasoning: {decision['reasoning'][:100]}...")
                else:
                    print(f"! Missing required keys in decision: {decision}")

        except json.JSONDecodeError as e:
            print(f"! Could not parse response as JSON: {e}")
            print(f"Raw response: {response_text[:500]}...")

        return True

    except Exception as e:
        print(f"✗ Error testing moderation simulation: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("LiteLLM Integration Test Suite")
    print("=" * 60)

    tests = [
        test_litellm_config,
        test_genai_client,
        test_config_manager,
        test_api_call,
        test_moderation_simulation,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test.__name__}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! LiteLLM integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
