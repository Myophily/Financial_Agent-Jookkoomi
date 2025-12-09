"""
JooKkoomi Tools Package

Provides 14 tools for stock analysis across 7 categories:
- Financial: get_financial_data, get_historical_data
- Search: tavily_search, google_news_search
- Sentiment: get_market_sentiment, scrap_reddit
- Technical: get_ta_data
- Guidance: get_guidance
- Macro: get_economic_indicator, get_global_environment, get_policy_environment, get_economic_cycle, get_fomc
- Trends: get_consumer_trends
"""

# Load environment variables before importing any tools
# This ensures USER_AGENT is available for pandas_datareader and other libraries
import os
from dotenv import load_dotenv
load_dotenv()

# Explicitly ensure USER_AGENT is set for pandas_datareader
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Import all tools from category modules
from .financial import get_financial_data, get_historical_data
from .search import tavily_search, google_news_search
from .sentiment import get_market_sentiment, scrap_reddit
from .technical import get_ta_data
from .guidance import get_guidance
from .macro import get_economic_indicator, get_global_environment, get_policy_environment, get_economic_cycle, get_fomc
from .trends import get_consumer_trends

# Tool registry (used by subgraph.py for dynamic dispatch)
# IMPORTANT: Maintain original order from tools.py line 1231
# Note: get_guidance added after get_market_sentiment for Part 9 usage
# Note: get_fomc added after get_economic_cycle for Part 13 usage
# Note: get_consumer_trends added after get_fomc for Part 13 usage
tools = [
    tavily_search,
    get_financial_data,
    get_historical_data,
    get_ta_data,
    google_news_search,
    get_market_sentiment,
    get_guidance,
    scrap_reddit,
    get_economic_indicator,
    get_global_environment,
    get_policy_environment,
    get_economic_cycle,
    get_fomc,
    get_consumer_trends
]

# Re-export individual tools for backward compatibility
__all__ = [
    'tools',
    'tavily_search',
    'get_financial_data',
    'get_historical_data',
    'get_ta_data',
    'google_news_search',
    'get_market_sentiment',
    'get_guidance',
    'scrap_reddit',
    'get_economic_indicator',
    'get_global_environment',
    'get_policy_environment',
    'get_economic_cycle',
    'get_fomc',
    'get_consumer_trends',
]
