"""
Company Guidance and Earnings Analysis Tools (FMP API)

Provides tools for fetching earnings reports, analyst estimates, and calendar events
from Financial Modeling Prep (FMP) API.
"""

import os
import time
import requests
from datetime import datetime, timedelta
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()
# ========== FMP API CONFIGURATION ==========
FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_TIMEOUT = 10  # seconds

# ==================== HELPER FUNCTIONS ====================

def check_fmp_api_health() -> tuple[bool, str]:
    """
    Quick health check for FMP API accessibility.

    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    api_key = os.getenv('FMP_API_KEY')
    if not api_key or api_key == "your-fmp-api-key-here":
        return False, "FMP_API_KEY not configured in .env"

    # Test with earnings endpoint (known to work in /stable API)
    url = f"{FMP_BASE_URL}/earnings"
    try:
        response = requests.get(url, params={'symbol': 'AAPL', 'apikey': api_key, 'limit': 1}, timeout=5)
        if response.status_code == 403:
            return False, "API key invalid (403 Forbidden)"
        if response.status_code == 402:
            return False, "API key lacks permissions (402 Payment Required)"
        if response.status_code == 404:
            return False, "FMP API endpoint not found (404) - check base URL"
        if response.status_code != 200:
            return False, f"API returned {response.status_code}"

        data = response.json()
        if not isinstance(data, list):
            return False, "API returned unexpected format"

        return True, "FMP API accessible"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except Exception as e:
        return False, f"Error: {type(e).__name__}"


def fetch_fmp_earnings_report(ticker: str) -> dict | None:
    """
    Fetch earnings report data using Yahoo Finance (up to 4 most recent quarters with actual data).

    Returns:
        dict: {
            'quarters': [{'date', 'fiscal_period', 'actual_eps', 'estimated_eps',
                         'surprise_pct', 'revenue', 'estimated_revenue'}],
            'ticker': str,
            'last_update': str
        } or None if failed
    """
    try:
        import yfinance as yf
        from datetime import datetime

        # Handle Korean stocks
        if ticker.isdigit():
            ticker = f"{ticker}.KS"

        stock = yf.Ticker(ticker)
        earnings = stock.earnings_dates  # Pandas DataFrame with historical earnings

        if earnings is None or earnings.empty:
            print(f"[Yahoo Finance] No earnings data for {ticker}")
            return None

        # Get last 4 quarters with actual data
        quarters = []
        for index, row in earnings.iterrows():
            if len(quarters) >= 4:
                break

            eps_est = row.get('EPS Estimate')
            reported_eps = row.get('Reported EPS')

            # Skip if either value is None or NaN
            import math
            if eps_est is None or reported_eps is None or math.isnan(eps_est) or math.isnan(reported_eps):
                continue

            surprise_pct = ((reported_eps - eps_est) / eps_est * 100) if eps_est != 0 else 0.0

            quarters.append({
                'date': index.strftime('%Y-%m-%d'),
                'fiscal_period': index.strftime('%Y-%m-%d'),
                'actual_eps': float(reported_eps),
                'estimated_eps': float(eps_est),
                'surprise_pct': surprise_pct,
                'revenue': 0,  # Yahoo Finance doesn't provide revenue in earnings_dates
                'estimated_revenue': 0
            })

        if not quarters:
            print(f"[Yahoo Finance] No historical earnings data found for {ticker}")
            return None

        return {
            'quarters': quarters,
            'ticker': ticker,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        print(f"[Yahoo Finance Earnings] Error: {type(e).__name__}: {str(e)[:200]}")
        return None


def fetch_fmp_analyst_estimates(ticker: str) -> dict | None:
    """
    Fetch analyst consensus estimates from FMP API (next 4 quarters).

    Returns:
        dict: {
            'estimates': [{'date', 'estimated_revenue_avg/high/low',
                          'estimated_eps_avg/high/low', 'number_of_analysts'}],
            'ticker': str
        } or None if failed
    """
    try:
        import os
        import requests

        api_key = os.getenv('FMP_API_KEY')
        if not api_key or api_key == "your-fmp-api-key-here":
            return None

        if ticker.isdigit():
            ticker = f"{ticker}.KS"

        url = f"{FMP_BASE_URL}/analyst-estimates"
        # /stable API requires 'period' parameter
        params = {'symbol': ticker, 'apikey': api_key, 'period': 'annual', 'limit': 4}

        response = requests.get(url, params=params, timeout=FMP_TIMEOUT)

        # Check HTTP status before parsing
        if response.status_code == 402:
            print(f"[FMP Analyst Estimates] Premium subscription required for {ticker}")
            return None
        elif response.status_code != 200:
            print(f"[FMP Analyst Estimates] HTTP {response.status_code}: {response.text[:200]}")
            return None

        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            print(f"[FMP Analyst Estimates] Empty or invalid response for {ticker}")
            return None

        estimates = []
        for item in data[:4]:
            # Updated field names for /stable API
            estimates.append({
                'date': item.get('date', 'N/A'),
                'estimated_revenue_avg': float(item.get('revenueAvg', 0)),
                'estimated_revenue_high': float(item.get('revenueHigh', 0)),
                'estimated_revenue_low': float(item.get('revenueLow', 0)),
                'estimated_eps_avg': float(item.get('epsAvg', 0)),
                'estimated_eps_high': float(item.get('epsHigh', 0)),
                'estimated_eps_low': float(item.get('epsLow', 0)),
                'number_of_analysts': int(item.get('numAnalystsRevenue', 0))
            })

        return {'estimates': estimates, 'ticker': ticker}
    except requests.exceptions.HTTPError as e:
        print(f"[FMP Analyst Estimates] HTTP Error: {e.response.status_code}")
        return None
    except requests.exceptions.Timeout:
        print(f"[FMP Analyst Estimates] Request timeout after {FMP_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"[FMP Analyst Estimates] Error: {type(e).__name__}: {str(e)[:200]}")
        return None


def fetch_fmp_earnings_calendar(ticker: str) -> dict | None:
    """
    Fetch upcoming earnings calendar for specific ticker from FMP API.

    Returns:
        dict: {
            'upcoming': [{'date', 'eps_estimate', 'revenue_estimate', 'fiscal_period'}],
            'ticker': str
        } or None if failed
    """
    try:
        import os
        import requests
        from datetime import datetime, timedelta

        api_key = os.getenv('FMP_API_KEY')
        if not api_key or api_key == "your-fmp-api-key-here":
            return None

        if ticker.isdigit():
            ticker = f"{ticker}.KS"

        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

        url = f"{FMP_BASE_URL}/earnings-calendar"
        params = {'symbol': ticker, 'apikey': api_key, 'from': today, 'to': future}

        response = requests.get(url, params=params, timeout=FMP_TIMEOUT)

        # Check HTTP status before parsing
        if response.status_code == 402:
            print(f"[FMP Earnings Calendar] Premium subscription required for {ticker}")
            return None
        elif response.status_code != 200:
            print(f"[FMP Earnings Calendar] HTTP {response.status_code}: {response.text[:200]}")
            return None

        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            print(f"[FMP Earnings Calendar] Empty or invalid response for {ticker}")
            return None

        upcoming = []
        for item in data:
            # Filter by symbol since API returns all symbols (not respecting query param)
            if item.get('symbol') != ticker:
                continue

            event_date = item.get('date', '')
            eps_est = item.get('epsEstimated')
            rev_est = item.get('revenueEstimated')

            # Only include future dates with non-None estimates
            if event_date >= today and eps_est is not None:
                upcoming.append({
                    'date': event_date,
                    'eps_estimate': float(eps_est),
                    'revenue_estimate': float(rev_est or 0),
                    'fiscal_period': event_date  # No fiscalDateEnding in /stable API
                })

        if not upcoming:
            print(f"[FMP Earnings Calendar] No upcoming earnings found for {ticker}")
            return None

        return {'upcoming': upcoming[:3], 'ticker': ticker}  # Max 3 dates
    except requests.exceptions.HTTPError as e:
        print(f"[FMP Earnings Calendar] HTTP Error: {e.response.status_code}")
        return None
    except requests.exceptions.Timeout:
        print(f"[FMP Earnings Calendar] Request timeout after {FMP_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"[FMP Earnings Calendar] Error: {type(e).__name__}: {str(e)[:200]}")
        return None


# ==================== MAIN TOOL ====================

@tool
def get_guidance(ticker: str) -> str:
    """
    Company Guidance and Earnings Analysis: Collect data from 3 sources via Yahoo Finance and FMP API.
    1) Earnings Reports & Surprises (Yahoo Finance - recent 4 quarters)
    2) Analyst Estimates (FMP - analyst consensus, next 4 quarters)
    3) Earnings Calendar (FMP - earnings announcement schedule, next 90 days)

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')
                     Yahoo Finance supports global stocks
                     FMP API is optimized for US stocks

    Returns:
        str: Summary of earnings and guidance analysis from 3 sources (formatted by section)
    """
    # === 1. Initialize ===
    is_korean_stock = ticker.isdigit()

    summary = f"--- COMPANY GUIDANCE & EARNINGS ANALYSIS ({ticker}) ---\n"
    summary += f"Stock Type: {'Korean (KS)' if is_korean_stock else 'US'}\n"
    summary += f"Data Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    failed_sources = []

    # API Key validation (common for all 4 sources)
    fmp_api_key = os.getenv('FMP_API_KEY')

    if not fmp_api_key or fmp_api_key == "your-fmp-api-key-here":
        summary += "=== FMP API KEY MISSING ===\n"
        summary += "[!] FMP API key not configured.\n"
        summary += "    Please add FMP_API_KEY to .env file.\n"
        summary += "    Register at https://financialmodelingprep.com/developer/docs\n\n"
        summary += "Note: This tool is optimized for US stocks; "
        summary += "Korean stocks may not be supported.\n"
        return summary

    # === 2. SOURCE 1: Earnings Reports & Surprises ===
    summary += "=== 1. EARNINGS REPORTS & SURPRISES (Yahoo Finance) ===\n"

    try:
        earnings_data = fetch_fmp_earnings_report(ticker)

        if earnings_data and earnings_data.get('quarters'):
            summary += f"Stock: {earnings_data['ticker']}\n"
            summary += f"Last Updated: {earnings_data.get('last_update', 'N/A')}\n\n"

            for quarter in earnings_data['quarters'][:4]:
                summary += f"[{quarter['fiscal_period']} - {quarter['date']}]\n"
                summary += f"  EPS: Actual ${quarter['actual_eps']:.2f} vs Est ${quarter['estimated_eps']:.2f} "
                summary += f"(Surprise: {quarter['surprise_pct']:+.2f}%)\n"

                if quarter['revenue'] > 0 and quarter['estimated_revenue'] > 0:
                    rev_surprise = ((quarter['revenue'] - quarter['estimated_revenue']) / quarter['estimated_revenue']) * 100
                    summary += f"  Revenue: ${quarter['revenue']/1e9:.2f}B vs Est ${quarter['estimated_revenue']/1e9:.2f}B "
                    summary += f"(Surprise: {rev_surprise:+.2f}%)\n"
                summary += "\n"
        else:
            summary += f"[!] {ticker} No earnings data (May not be supported by Yahoo Finance)\n\n"
            failed_sources.append("Yahoo Finance Earnings")

    except Exception as e:
        summary += f"[!] Yahoo Finance Earnings collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("Yahoo Finance Earnings")

    time.sleep(0.5)  # Rate limiting

    # === 3. SOURCE 2: Analyst Estimates ===
    summary += "=== 2. ANALYST ESTIMATES (FMP) ===\n"

    try:
        analyst_data = fetch_fmp_analyst_estimates(ticker)

        if analyst_data and analyst_data.get('estimates'):
            summary += f"Stock: {analyst_data['ticker']}\n"
            summary += "Consensus Forward Estimates:\n\n"

            for estimate in analyst_data['estimates'][:4]:
                summary += f"[{estimate['date']}]\n"
                summary += f"  Revenue Est: ${estimate['estimated_revenue_avg']/1e9:.2f}B "
                summary += f"(Range: ${estimate['estimated_revenue_low']/1e9:.2f}B - ${estimate['estimated_revenue_high']/1e9:.2f}B)\n"
                summary += f"  EPS Est: ${estimate['estimated_eps_avg']:.2f} "
                summary += f"(Range: ${estimate['estimated_eps_low']:.2f} - ${estimate['estimated_eps_high']:.2f})\n"
                summary += f"  Analysts: {estimate['number_of_analysts']}\n\n"
        else:
            summary += f"[!] {ticker} No analyst forecasts\n\n"
            failed_sources.append("FMP Analyst Estimates")

    except Exception as e:
        summary += f"[!] FMP Analyst Estimates collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("FMP Analyst Estimates")

    time.sleep(0.5)

    # === 4. SOURCE 3: Earnings Calendar ===
    summary += "=== 3. EARNINGS CALENDAR - UPCOMING (FMP) ===\n"

    try:
        earnings_cal = fetch_fmp_earnings_calendar(ticker)

        if earnings_cal and earnings_cal.get('upcoming'):
            summary += f"Stock: {earnings_cal['ticker']}\n"
            summary += f"Upcoming Earnings ({len(earnings_cal['upcoming'])} dates):\n\n"

            for upcoming in earnings_cal['upcoming'][:3]:
                summary += f"- {upcoming['date']} ({upcoming['fiscal_period']})\n"
                summary += f"  EPS Est: ${upcoming['eps_estimate']:.2f} | "
                summary += f"Revenue Est: ${upcoming['revenue_estimate']/1e9:.2f}B\n"
            summary += "\n"
        else:
            summary += f"[!] {ticker} No scheduled earnings announcements\n\n"
            failed_sources.append("FMP Earnings Calendar")

    except Exception as e:
        summary += f"[!] FMP Earnings Calendar collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("FMP Earnings Calendar")

    time.sleep(0.5)

    # === 6. Summary ===
    summary += "=== SUMMARY ===\n"

    sources_collected = 3 - len(set(failed_sources))
    summary += f"Data Sources Collected: {sources_collected}/3"
    if sources_collected == 3:
        summary += " ✓"
    summary += "\n"

    if failed_sources:
        summary += f"Failed Sources: {', '.join(set(failed_sources))}\n"

    summary += "\nNote: Yahoo Finance provides earnings data; FMP provides analyst estimates and earnings calendar.\n"
    summary += "Note: Based on the latest publicly available values at the time of data collection.\n"

    return summary
