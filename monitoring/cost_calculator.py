# monitoring/cost_calculator.py

"""
Cost calculation for Gemini API usage.
Based on official Gemini pricing as of 2025.
"""

from typing import Optional, Dict


# Gemini API Pricing (2025)
# Prices are per 1 million tokens
PRICING = {
    "gemini-2.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000  
    },
    "gemini-2.5-flash": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000  
    },
    "gemini-2.5-pro": {
        "input": 1.25 / 1_000_000, 
        "output": 5.00 / 1_000_000  
    }
}


def calculate_cost(model_name: str, token_usage: Optional[Dict[str, int]]) -> float:
    """
    Calculate cost in USD for a single LLM call.

    Args:
        model_name: Gemini model name (e.g., "gemini-2.5-flash")
        token_usage: Dictionary with input_tokens and output_tokens, or None

    Returns:
        Cost in USD (rounded to 6 decimal places), or 0.0 if token_usage is None
    """
    if not token_usage:
        return 0.0

    # Get pricing for model (default to flash if unknown)
    pricing = PRICING.get(model_name, PRICING["gemini-2.5-flash"])

    # Calculate costs
    input_cost = token_usage.get("input_tokens", 0) * pricing["input"]
    output_cost = token_usage.get("output_tokens", 0) * pricing["output"]

    total_cost = input_cost + output_cost

    return round(total_cost, 6)


def get_model_name_from_response(response) -> str:
    """
    Extract model name from Gemini API response metadata.

    Args:
        response: LangChain AI message response

    Returns:
        Model name string, defaults to "gemini-2.5-flash"
    """
    try:
        if hasattr(response, 'response_metadata'):
            # Try to extract model name from metadata
            model = response.response_metadata.get('model_name', '')
            if model:
                return model

        # Default to flash
        return "gemini-2.5-flash"

    except (AttributeError, KeyError):
        return "gemini-2.5-flash"
