"""
Consumer Trends Analysis Tool

Tracks consumer interest changes using Google Trends (pytrends) for stock analysis.
Analyzes both company-specific and industry-level keywords over a 6-month period.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
from langchain_core.tools import tool

# Constants
DEFAULT_TIMEFRAME = 'today 3-m'  # 3 months (6-month format not supported by Google Trends)
MAX_KEYWORDS = 5                  # pytrends limit
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2            # seconds
TOKEN_TARGET_MAX = 2000           # token optimization


def extract_keywords_from_ticker(ticker: str) -> Dict[str, any]:
    """
    Extract company name and industry keywords from ticker using yfinance.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', '005930')

    Returns:
        dict: {
            'company_name': str,
            'company_keywords': list[str],
            'industry_keywords': list[str],
            'all_keywords': list[str]  # max 5 items
        }
    """
    try:
        # Handle Korean stocks (numeric tickers)
        ticker_symbol = f"{ticker}.KS" if ticker.isdigit() else ticker

        # Fetch company info
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        # Extract basic info
        company_name = info.get('shortName', info.get('longName', ticker))
        industry = info.get('industry', '')
        sector = info.get('sector', '')

        # Clean company name (remove Inc., Corp, Ltd., etc.)
        cleaned_name = company_name
        for suffix in [' Inc.', ' Corp.', ' Corporation', ' Ltd.', ' Limited', ' Co.', ' LLC', ' PLC']:
            cleaned_name = cleaned_name.replace(suffix, '')
        cleaned_name = cleaned_name.strip()

        # Build keyword lists
        company_keywords = [cleaned_name]

        # Add alternative company name if significantly different
        if company_name != cleaned_name and len(company_keywords) < MAX_KEYWORDS:
            company_keywords.append(company_name.split()[0])  # First word only

        industry_keywords = []

        # Add industry keywords
        if industry:
            industry_keywords.append(industry)

        # Add sector if different from industry and space available
        if sector and sector != industry:
            industry_keywords.append(sector)

        # Combine all keywords (max 5)
        all_keywords = []
        all_keywords.extend(company_keywords[:2])  # Max 2 company variants
        all_keywords.extend(industry_keywords[:3])  # Max 3 industry/sector
        all_keywords = all_keywords[:MAX_KEYWORDS]  # Enforce max limit

        # Remove duplicates while preserving order
        seen = set()
        all_keywords = [k for k in all_keywords if not (k in seen or seen.add(k))]

        return {
            'company_name': cleaned_name,
            'company_keywords': company_keywords,
            'industry_keywords': industry_keywords,
            'all_keywords': all_keywords
        }

    except Exception as e:
        # Fallback: use ticker as keyword
        return {
            'company_name': ticker,
            'company_keywords': [ticker],
            'industry_keywords': [],
            'all_keywords': [ticker]
        }


def fetch_trends_with_retry(pytrends, kw_list: List[str], max_retries: int = MAX_RETRIES) -> Optional[pd.DataFrame]:
    """
    Fetch Google Trends data with exponential backoff retry.

    Args:
        pytrends: TrendReq instance
        kw_list (list): List of keywords to query
        max_retries (int): Maximum number of retry attempts

    Returns:
        DataFrame or None: Interest over time data, or None if failed
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            pytrends.build_payload(
                kw_list=kw_list,
                timeframe=DEFAULT_TIMEFRAME,
                geo='',  # Global tracking
                gprop=''  # Web search
            )
            df = pytrends.interest_over_time()
            return df

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = RETRY_BACKOFF_BASE ** attempt
                time.sleep(sleep_time)
            else:
                # Final failure
                return None

    return None


def analyze_interest_over_time(df: pd.DataFrame, keyword: str) -> Optional[Dict]:
    """
    Analyze trend metrics from interest_over_time DataFrame.

    Args:
        df (DataFrame): Interest over time data from pytrends
        keyword (str): Keyword to analyze

    Returns:
        dict: {
            'latest': int,
            'avg': float,
            'trend': str,  # 'rising', 'falling', 'stable'
            'change_pct': float,
            'peak': int,
            'trough': int,
            'peak_date': str,
            'trough_date': str
        } or None if insufficient data
    """
    try:
        if df is None or df.empty or keyword not in df.columns:
            return None

        series = df[keyword]

        # Remove any non-numeric values
        series = pd.to_numeric(series, errors='coerce').dropna()

        if len(series) == 0:
            return None

        # Calculate metrics
        latest = int(series.iloc[-1])
        avg = float(series.mean())
        peak = int(series.max())
        trough = int(series.min())

        peak_date = series.idxmax().strftime('%b %d') if hasattr(series.idxmax(), 'strftime') else 'N/A'
        trough_date = series.idxmin().strftime('%b %d') if hasattr(series.idxmin(), 'strftime') else 'N/A'

        # Calculate change percentage
        change_pct = ((latest - avg) / avg * 100) if avg > 0 else 0

        # Determine trend direction
        if change_pct > 5:
            trend = 'Rising'
        elif change_pct < -5:
            trend = 'Falling'
        else:
            trend = 'Stable'

        return {
            'latest': latest,
            'avg': round(avg, 1),
            'trend': trend,
            'change_pct': round(change_pct, 1),
            'peak': peak,
            'trough': trough,
            'peak_date': peak_date,
            'trough_date': trough_date
        }

    except Exception as e:
        return None


def format_keyword_section(keyword: str, interest_data: Optional[Dict], related_queries: Optional[Dict]) -> str:
    """
    Format single keyword analysis section.

    Args:
        keyword (str): Keyword being analyzed
        interest_data (dict): Analysis from analyze_interest_over_time()
        related_queries (dict): Related queries data from pytrends

    Returns:
        str: Formatted section (~200-300 tokens)
    """
    output = f'Keyword: "{keyword}"\n'

    if interest_data is None:
        output += "Status: Insufficient search volume\n\n"
        return output

    # Interest metrics
    output += f"Latest: {interest_data['latest']}/100 | 3M Avg: {interest_data['avg']}/100\n"
    output += f"Trend: {interest_data['trend']} ({interest_data['change_pct']:+.1f}%) | "
    output += f"Peak: {interest_data['peak']}/100 ({interest_data['peak_date']}) | "
    output += f"Trough: {interest_data['trough']}/100 ({interest_data['trough_date']})\n"

    # Related queries (if available)
    if related_queries and keyword in related_queries:
        keyword_queries = related_queries[keyword]

        # Rising queries
        if keyword_queries['rising'] is not None and not keyword_queries['rising'].empty:
            output += "\nRelated Queries (Rising):\n"
            rising = keyword_queries['rising'].head(5)
            for idx, row in enumerate(rising.itertuples(), 1):
                query = row.query if hasattr(row, 'query') else 'N/A'
                value = row.value if hasattr(row, 'value') else 'N/A'
                output += f"{idx}. {query} (+{value})\n"

        # Top queries
        if keyword_queries['top'] is not None and not keyword_queries['top'].empty:
            output += "\nRelated Queries (Top):\n"
            top = keyword_queries['top'].head(5)
            for idx, row in enumerate(top.itertuples(), 1):
                query = row.query if hasattr(row, 'query') else 'N/A'
                value = row.value if hasattr(row, 'value') else 'N/A'
                output += f"{idx}. {query} ({value})\n"

    output += "\n"
    return output


def format_comparative_analysis(company_data: Optional[Dict], industry_data: List[Optional[Dict]]) -> str:
    """
    Generate comparative analysis between company and industry.

    Args:
        company_data (dict): Company keyword analysis data
        industry_data (list): List of industry keyword analysis data

    Returns:
        str: Analysis section (~200 tokens)
    """
    output = "=== 3. COMPARATIVE ANALYSIS ===\n\n"

    if company_data is None:
        output += "Company data unavailable for comparison.\n\n"
        return output

    # Calculate industry average (only from valid data)
    valid_industry_data = [d for d in industry_data if d is not None]

    if len(valid_industry_data) == 0:
        output += f"Company Interest: {company_data['latest']}/100\n"
        output += "Industry data unavailable for comparison.\n\n"
        return output

    industry_avg = sum(d['latest'] for d in valid_industry_data) / len(valid_industry_data)

    # Compare company vs industry
    diff = company_data['latest'] - industry_avg

    output += f"Company vs. Industry Interest:\n"
    output += f"- Company: {company_data['latest']}/100\n"
    output += f"- Industry avg: {industry_avg:.1f}/100\n"

    if diff > 10:
        output += f"- Interpretation: Strong brand dominance (outperforming +{diff:.0f} pts)\n"
    elif diff > 0:
        output += f"- Interpretation: Moderate brand strength (+{diff:.0f} pts)\n"
    elif diff > -10:
        output += f"- Interpretation: Aligned with industry ({diff:+.0f} pts)\n"
    else:
        output += f"- Interpretation: Below industry average ({diff:+.0f} pts)\n"

    # Trend alignment
    company_trend = company_data['trend']
    industry_trends = [d['trend'] for d in valid_industry_data]
    aligned = sum(1 for t in industry_trends if t == company_trend)

    output += f"\nTrend Alignment:\n"
    output += f"- Company trend: {company_trend}\n"
    output += f"- Industry alignment: {aligned}/{len(industry_trends)} keywords match\n"

    if aligned == len(industry_trends):
        output += "- Signal: Moving in sync with industry\n"
    elif aligned > len(industry_trends) / 2:
        output += "- Signal: Partially aligned with industry trends\n"
    else:
        output += "- Signal: Diverging from industry trends\n"

    output += "\n"
    return output


def generate_insights(all_data: Dict, related_queries_all: Optional[Dict], keywords_info: Dict) -> str:
    """
    Generate key insights from all collected data.

    Args:
        all_data (dict): All interest_over_time analysis data
        related_queries_all (dict): All related queries data
        keywords_info (dict): Keyword extraction results

    Returns:
        str: Bullet-point insights (~150 tokens)
    """
    output = "=== 4. KEY INSIGHTS ===\n\n"

    insights = []

    # Company interest analysis
    company_kw = keywords_info['company_keywords'][0] if keywords_info['company_keywords'] else None
    if company_kw and company_kw in all_data and all_data[company_kw]:
        data = all_data[company_kw]
        if data['trend'] == 'Rising':
            insights.append(f"Strong consumer interest momentum ({data['change_pct']:+.1f}% vs 3M avg)")
        elif data['trend'] == 'Falling':
            insights.append(f"Declining consumer interest ({data['change_pct']:+.1f}% vs 3M avg)")
        else:
            insights.append(f"Stable consumer interest (flat vs 3M avg)")

    # Industry trends
    industry_keywords = keywords_info['industry_keywords']
    if industry_keywords:
        industry_data_list = [all_data.get(kw) for kw in industry_keywords if kw in all_data]
        valid_industry = [d for d in industry_data_list if d is not None]

        if valid_industry:
            rising_count = sum(1 for d in valid_industry if d['trend'] == 'Rising')
            if rising_count == len(valid_industry):
                insights.append("Industry-wide consumer interest is growing across all tracked sectors")
            elif rising_count > len(valid_industry) / 2:
                insights.append("Mixed industry trends with majority showing rising interest")
            else:
                insights.append("Industry-level consumer interest showing weakness")

    # Related queries insights
    if related_queries_all and company_kw and company_kw in related_queries_all:
        queries = related_queries_all[company_kw]
        if queries and queries['rising'] is not None and not queries['rising'].empty:
            top_rising = queries['rising'].head(1)
            if not top_rising.empty:
                top_query = top_rising.iloc[0]['query'] if 'query' in top_rising.columns else 'product features'
                insights.append(f"Top rising search: '{top_query}' indicates emerging consumer interest")

    # Fallback if no insights generated
    if not insights:
        insights.append("Limited data available for trend analysis")

    for insight in insights[:4]:  # Max 4 insights for token optimization
        output += f"- {insight}\n"

    output += "\n"
    return output


@tool
def get_consumer_trends(ticker: str) -> str:
    """
    Consumer interest trend analysis using Google Trends.

    Tracks both company/brand names AND industry-level keywords over
    the past 3 months to identify consumer interest changes.

    Args:
        ticker (str): Stock ticker symbol
            - Numeric = Korean stock (e.g., "005930")
            - Alphabetic = US stock (e.g., "AAPL")

    Returns:
        str: Formatted consumer trends report including:
            - Company brand interest (search volume trends)
            - Industry interest (sector-level trends)
            - Related rising/top queries
            - Comparative analysis
            - Key insights and trend direction

    Data Source: Google Trends (3-month period, global tracking)
    Output Size: ~1,500-2,000 tokens (token-optimized)

    Example:
        >>> result = get_consumer_trends("AAPL")
        >>> print(result)
        --- CONSUMER TRENDS ANALYSIS (AAPL) ---
        Collection Time: 2025-11-29 14:30
        ...

    Note:
        - Google Trends API has rate limits (~50-100 requests/hour)
        - Returns partial results if some keywords lack sufficient data
        - Korean stocks use English company names from yfinance
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return "[!] Error: pytrends library not installed. Run: pip install pytrends"

    # Initialize output
    summary = f"--- CONSUMER TRENDS ANALYSIS ({ticker}) ---\n"
    summary += f"Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    summary += f"Period: 3 months ({DEFAULT_TIMEFRAME})\n\n"

    # Step 1: Extract keywords
    keywords_info = extract_keywords_from_ticker(ticker)
    all_keywords = keywords_info['all_keywords']

    if not all_keywords:
        return f"{summary}[!] Error: Could not extract keywords for ticker '{ticker}'\n"

    # Step 2: Initialize pytrends with proper headers
    try:
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(10, 25),
            requests_args={
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            }
        )
    except Exception as e:
        return f"{summary}[!] Error initializing Google Trends: {str(e)[:100]}\n"

    # Step 3: Fetch trends data
    interest_df = fetch_trends_with_retry(pytrends, all_keywords)

    if interest_df is None or interest_df.empty:
        return f"{summary}[!] Error: Could not fetch Google Trends data. Possible rate limiting or insufficient search volume.\n"

    # Step 4: Fetch related queries
    related_queries = None
    try:
        related_queries = pytrends.related_queries()
    except Exception as e:
        # Continue without related queries
        pass

    # Step 5: Analyze each keyword
    all_data = {}
    for keyword in all_keywords:
        all_data[keyword] = analyze_interest_over_time(interest_df, keyword)

    # Step 6: Format output sections

    # Section 1: Company Brand Interest
    summary += "=== 1. COMPANY BRAND INTEREST ===\n\n"
    company_keywords = keywords_info['company_keywords']
    company_data = None

    for kw in company_keywords:
        if kw in all_data:
            summary += format_keyword_section(kw, all_data[kw], related_queries)
            if company_data is None:
                company_data = all_data[kw]  # Use first company keyword for comparison

    # Section 2: Industry Interest
    summary += "=== 2. INDUSTRY INTEREST ===\n\n"
    industry_keywords = keywords_info['industry_keywords']
    industry_data_list = []

    if industry_keywords:
        for kw in industry_keywords:
            if kw in all_data:
                summary += format_keyword_section(kw, all_data[kw], related_queries)
                industry_data_list.append(all_data[kw])
    else:
        summary += "No industry keywords available.\n\n"

    # Section 3: Comparative Analysis
    summary += format_comparative_analysis(company_data, industry_data_list)

    # Section 4: Key Insights
    summary += generate_insights(all_data, related_queries, keywords_info)

    # Summary statistics
    successful_keywords = sum(1 for d in all_data.values() if d is not None)
    total_keywords = len(all_keywords)

    summary += "=== SUMMARY ===\n"
    summary += f"Keywords: {successful_keywords}/{total_keywords} ✓ | "

    if successful_keywords == total_keywords:
        summary += "Data Quality: High | "
    elif successful_keywords >= total_keywords / 2:
        summary += "Data Quality: Medium | "
    else:
        summary += "Data Quality: Low | "

    # Signal strength
    if company_data:
        if company_data['trend'] == 'Rising' and company_data['change_pct'] > 10:
            summary += "Signal: Strong positive momentum\n"
        elif company_data['trend'] == 'Rising':
            summary += "Signal: Moderate positive momentum\n"
        elif company_data['trend'] == 'Falling' and company_data['change_pct'] < -10:
            summary += "Signal: Significant negative momentum\n"
        elif company_data['trend'] == 'Falling':
            summary += "Signal: Moderate negative momentum\n"
        else:
            summary += "Signal: Neutral/stable interest\n"
    else:
        summary += "Signal: Insufficient data\n"

    return summary
