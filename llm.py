# llm.py
# LLM initialization and configuration for JooKkoomi Stock Analysis Agent

import os
import warnings
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

# Load environment variables from .env file
load_dotenv()

# Load API keys (unified logic with fallback)
google_api_key = os.getenv("GOOGLE_API_KEY")
pro_api_key = os.getenv("GOOGLE_API_KEY_FLASH")
if not pro_api_key:
    pro_api_key = google_api_key  # Fallback


stop_char = ["\u00a0" * 10]

# === Define the Brain (LLM) ===
# Configure automatic retry on rate limit errors
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.3,
    google_api_key=google_api_key,
    stop=stop_char,
    model_kwargs={         
        "generation_config": {
            "thinking_config": {
                "thinking_budget": -1
            }
        }
    }
)

# === Define the Pro Brain (gemini-2.5-pro for report unification) ===
if pro_api_key:
    model_pro = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        google_api_key=pro_api_key,
    )
else:
    model_pro = None

# === Define the Flash Brain (gemini-2.5-flash) ===
if pro_api_key:
    model_flash = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.0,
        google_api_key=pro_api_key,
    )
else:
    model_flash = None


# Bind tools to model
# Two-stage initialization prevents circular dependency issues
from tools import tools
model_with_tools = model.bind_tools(tools)


# === String Output Parser ===
# Ensures all model outputs are strings, handling both string and list response.content types
str_parser = StrOutputParser()

# Create string-returning versions of models
# These chains automatically convert response to string using StrOutputParser
model_str = model | str_parser  # For tool-less invocations
model_pro_str = model_pro | str_parser if model_pro else None  # For unification
model_flash_str = model_flash | str_parser if model_flash else None  # For search processing

# Note: model_with_tools is kept as-is (returns AIMessage with tool_calls)
# We extract .content manually after tool execution completes using str_parser