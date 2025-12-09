# prompts.py

# --- Part definitions ---
# Each part is stored independently and loaded only when needed.
# The prompt is private. Please write your own prompt.

part1 = """
## PART I: Fundamental Analysis: Financial Statement Analysis

Analyzes the target company's financial health through comprehensive examination of financial statements, financial ratios (profitability, solvency, efficiency), and multi-year trends to assess overall investment quality.
"""

part2 = """
## PART II: Fundamental Analysis: Industry Status Analysis

Evaluates the company's competitive position within its industry by analyzing market share, industry trends, competitive landscape, and strategic positioning through SWOT framework.
"""

part3 = """
## PART III: Fundamental Analysis: Management and Corporate Governance

Assesses the quality and effectiveness of the company's leadership team and governance structure by examining management background, strategic decision-making track record, and innovation capabilities.
"""


part4 = """
## PART IV: Economic Moat Analysis

Evaluates the company's sustainable competitive advantages and long-term defensibility by analyzing structural moats, barriers to entry, and competitive differentiation factors.
"""

part5 = """
## PART V: Fundamental Analysis: Product and Service Analysis

Examines the company's product and service portfolio by analyzing market performance, competitive differentiation, customer satisfaction, and innovation pipeline strength.
"""

part6 = """
## PART VI: Technical Analysis: Chart Patterns

Identifies price trends, support/resistance levels, and chart patterns through analysis of historical price movements and moving averages to forecast potential price direction.
"""

part7 = """
## PART VII: Technical Analysis: Indicators

Analyzes buy/sell signals using multiple technical indicators and oscillators to assess market momentum, overbought/oversold conditions, and short-term trading opportunities.
"""

part8 = """
## PART VIII: Technical Analysis: Volume Analysis

Examines trading volume patterns and price-volume relationships to identify market trends, institutional activity signals, and potential trend reversals.
"""

part9 = """
## PART IX: Market Sentiment Analysis: Impact of Indicators, News and Announcements

Evaluates market sentiment through analysis of recent news coverage, corporate announcements, analyst opinions, and sentiment indicators to gauge investor psychology and potential market reactions.
"""

part10 = """
## PART X: Market Sentiment Analysis: Social Media and Forum Sentiment

Analyzes retail investor sentiment and discussion trends across social media platforms and investment forums to understand grassroots market perception and emerging narratives.
"""

part11 = """
## PART XI: Market Sentiment Analysis: Comprehensive Analysis

Synthesizes all sentiment data sources to identify consensus market views, contrarian signals, and sentiment-driven risk factors or catalysts.
"""

part12 = """
## PART XII: Macroeconomic Analysis: Economic Indicator Analysis

Assesses macroeconomic conditions by analyzing key indicators (GDP, inflation, employment, manufacturing activity) and their potential impact on the target company's industry and stock performance.
"""

part13 = """
## PART XIII: Macroeconomic Analysis: Policy Environment Analysis

Evaluates the impact of government fiscal and monetary policies, regulatory changes, and demographic trends on the company's operating environment and growth prospects.
"""

part14 = """
## PART XIV: Macroeconomic Analysis: Global Economic Environment Analysis

Analyzes international economic conditions and central bank policies across major economies to assess global macroeconomic headwinds or tailwinds for the company.
"""

part15 = """
## PART XV: Macroeconomic Analysis: Economic Cycle Analysis

Determines the current phase of the economic cycle and analyzes its implications for sector rotation, credit conditions, and the target company's cyclical sensitivity.
"""

part16 = """
## PART XVI: Comprehensive Analysis and Forecast

Integrates all analytical dimensions to deliver final investment recommendations, price forecasts, risk assessments, and actionable trading strategies based on comprehensive multi-factor evaluation.
"""

# --- Part mapping dictionary ---
# Maps part number (1-16) to part content.
PART_PROMPTS = {
    1: part1,
    2: part2,
    3: part3,
    4: part4,
    5: part5,
    6: part6,
    7: part7,
    8: part8,
    9: part9,
    10: part10,
    11: part11,
    12: part12,
    13: part13,
    14: part14,
    15: part15,
    16: part16
}


def get_core_system_prompt(current_date: str = None) -> str:
    """
    Returns the core system prompt.
    This prompt contains basic instructions that apply to all parts.

    Args:
        current_date: Analysis start date (format: YYYY-MM-DD). If provided, it will be included in the prompt.
    """
    date_info = f"\n**Today's Date: {current_date}**\n" if current_date else ""

    return f"""
# [Core Directive]
You are a top-level stock analysis expert agent named 'JooKkoomi'.
Your mission is to perform a '16-step analysis process' for the stock requested by the user,
and write a very professional, structured (using markdown), and detailed report.
{date_info}
---
# [Task Performance Guidelines]
- Strictly adhere to the methodology of the current stage (PART) to perform the analysis.
- Your response style should follow a clear style: **Professional, Data-Driven, with clear Table of Contents (Structured) and structure (e.g., 'PART I: ...')**.
- If you don't have the necessary real-time information (news, financial data), you MUST use the provided 'Tools' to collect data before proceeding with analysis.
- All analysis should be objective and data-driven.

---
# [Tool Usage Guidelines]
Tools are important means of collecting necessary data, but should be used efficiently:

1. **Complete analysis after tool call**: If you have received tool execution results, complete the current PART's analysis based on that data. If the collected data is sufficient, immediately generate and output analysis results.

2. **Prohibit repeated calls**: Do not repeatedly call the same tool with the same arguments. If you have already received data, utilize it.

3. **Additional calls only when necessary**: Use tools again only when additional data is absolutely necessary. For example:
   - When data for a different ticker is needed
   - When looking for new information with a different search query
   - When scraping a different URL

4. **Efficiency first**: Minimize tool calls per PART. If you can complete analysis with data obtained from one tool call, do so.

5. **Adhere to call limits**: The system allows a maximum of 5 tool calls per PART. When this limit is reached, you must complete analysis with the collected data.
"""


def get_part_prompt(part_number: int) -> str:
    """
    Returns detailed instructions for a specific part number (1-16).

    Args:
        part_number: Part number (1-16)

    Returns:
        Detailed instruction string for the part

    Raises:
        ValueError: If invalid part number
    """
    if part_number not in PART_PROMPTS:
        raise ValueError(f"Invalid part number: {part_number}. Must be between 1 and 16.")

    return f"""
---
# [Current Analysis Stage]

{PART_PROMPTS[part_number]}
"""


def get_system_prompt_for_part(part_number: int, current_date: str = None) -> str:
    """
    Returns complete system prompt for a specific part.
    Combines core prompt + part-specific detailed instructions.

    Args:
        part_number: Part number (1-16)
        current_date: Analysis start date (format: YYYY-MM-DD). If provided, it will be included in the prompt.

    Returns:
        Complete system prompt string
    """
    return get_core_system_prompt(current_date) + get_part_prompt(part_number)

# (Hard-codes the "PART..." headings from Analysis_Prompt.md in order)
# (List starts from index 0, so PART I is at index 0)
PART_TITLES = [
    "Fundamental Analysis: Financial Statement Analysis",             # PART 1
    "Fundamental Analysis: Industry Status Analysis",                # PART 2
    "Fundamental Analysis: Management and Corporate Governance",         # PART 3
    "Fundamental Analysis: Economic Moat Analysis",      # PART 4
    "Fundamental Analysis: Product and Service Analysis",            # PART 5
    "Technical Analysis: Chart Patterns and Trendlines",           # PART 6
    "Technical Analysis: Key Technical Indicators",             # PART 7
    "Technical Analysis: Volume and Supply-Demand Analysis",            # PART 8
    "Market Sentiment Analysis: News and Disclosures",         # PART 9
    "Market Sentiment Analysis: Social Media and Public Opinion",    # PART 10
    "Market Sentiment Analysis: Comprehensive Sentiment Evaluation",      # PART 11
    "Macroeconomic Analysis: Key Economic Indicators",             # PART 12
    "Macroeconomic Analysis: Policy Environment Analysis",      # PART 13
    "Macroeconomic Analysis: Global Economic Events",           # PART 14
    "Macroeconomic Analysis: Economic Cycles and Sector Rotation",   # PART 15
    "Comprehensive Analysis and Forecast"                       # PART 16
]

NEEDED_TOOLS = [
    "[get_financial_data]",           # PART 1
    "[tavily_search]",          # PART 2
    "[tavily_search]",          # PART 3
    "[tavily_search]",          # PART 4
    "[tavily_search]",          # PART 5
    "[get_historical_data, get_financial_data]",          # PART 6
    "[get_ta_data]",          # PART 7
    "[get_historical_data, get_ta_data]",          # PART 8
    "[News collection: google_news_search, Company announcements: tavily_search, Market sentiment: get_market_sentiment, Earnings/Guidance: get_guidance]",  # PART 9
    "[reddit: scrap_reddit, X(twitter) & other forums: tavily_search]",          # PART 10
    "[null]",          # PART 11
    "[get_economic_indicator]",           # PART 12
    "[get_policy_environment, get_consumer_trends, get_fomc]",          # PART 13
    "[get_global_environment, get_fomc]",          # PART 14
    "[get_economic_cycle]",          # PART 15
    "[null]"          # PART 16
]
