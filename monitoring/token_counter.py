# monitoring/token_counter.py

"""
Token usage extraction from Gemini API responses.
Only records token usage when available from API metadata.
"""

from typing import Optional, Dict


def extract_token_usage(response) -> Optional[Dict[str, int]]:
    """
    Extract token usage from Gemini API response metadata.

    Per user preference: Returns None if token metadata is not available
    (skips token counting on failures rather than estimating).

    Args:
        response: LangChain AI message response from Gemini API

    Returns:
        Dictionary with input_tokens, output_tokens, total_tokens or None if unavailable
    """
    try:
        # Gemini models return usage metadata in response_metadata
        if not hasattr(response, 'response_metadata'):
            return None

        usage = response.response_metadata.get('usage_metadata', {})

        if not usage:
            return None  # Skip token counting if not available

        # Extract token counts
        input_tokens = usage.get('prompt_token_count', 0)
        output_tokens = usage.get('candidates_token_count', 0)
        total_tokens = usage.get('total_token_count', 0)

        # Validate that we got actual data
        if total_tokens == 0 and input_tokens == 0 and output_tokens == 0:
            return None

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }

    except (AttributeError, KeyError, TypeError):
        # Gracefully skip if metadata structure is unexpected
        return None
