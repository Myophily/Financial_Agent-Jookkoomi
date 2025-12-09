# tools/macro.py
# Macroeconomic data collection tools for Part 12 analysis

import time
import asyncio
import os
import requests
from datetime import datetime, timedelta
from langchain.tools import tool
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright
import warnings
from dotenv import load_dotenv

load_dotenv()

# Explicitly ensure USER_AGENT is set in os.environ for pandas_datareader
# This prevents pandas_datareader warning even if it's already in .env
if "USER_AGENT" not in os.environ:
    os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

warnings.simplefilter(action='ignore', category=FutureWarning)

# ==================== HELPER FUNCTIONS ====================

async def async_load_with_retry(url, selectors_to_remove=None):
    """
    Async helper function to load web pages using Playwright with custom User-Agent.

    Args:
        url (str): URL to fetch
        selectors_to_remove (list, optional): CSS selectors to remove from page (unused)

    Returns:
        str: HTML content of the page, or None if loading failed
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # [Load USER_AGENT from .env, use default if not found]
        user_agent = os.getenv(
            "USER_AGENT", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        context = await browser.new_context(
            user_agent=user_agent
        )
        
        page = await context.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = await page.content()
            return content
        except Exception as e:
            print(f"Error loading {url}: {e}")
            return None
        finally:
            await browser.close()


def scrape_ism_pmi(retry_count=0, max_retries=2):
    """
    Scrape ISM Manufacturing PMI from investing.com using Regex on text content.
    """
    try:
        url = "https://www.investing.com/economic-calendar/ism-manufacturing-pmi-173"
        selectors_to_remove = ['header', 'footer', 'nav', '.advertisement', '.banner']

        print(f"Attempting to fetch URL (Try {retry_count+1})...")

        # Async load
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html_content = loop.run_until_complete(
            async_load_with_retry(url, selectors_to_remove)
        )
        loop.close()

        if not html_content:
            print("Failed to retrieve HTML content.")
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # Find releaseInfo
        release_info = soup.find('div', id='releaseInfo')
        if not release_info:
            print("Warning: 'releaseInfo' div not found. Using full body text.")
            release_info = soup

        # --- [Core fix] Get full text and parse with Regex ---
        # Don't rely on HTML tag structure, get all visible text on screen
        # Example: "Latest Release Nov 03, 2025 Actual 46.5 Forecast 47.6 Previous 47.2"
        full_text = release_info.get_text(separator=' ', strip=True)
        
        # For debugging: print parsing target text (for failure analysis)
        # print(f"[Debug] Raw Text: {full_text[:100]}...") 

        result = {}

        # 1. Extract date (pattern: "MMM DD, YYYY")
        # Example: Nov 03, 2025 or Oct 01, 2025
        date_match = re.search(r'([A-Z][a-z]{2}\s\d{1,2},\s\d{4})', full_text)
        if date_match:
            result['date'] = date_match.group(1)

        # 2. Value extraction function (flexible pattern matching)
        def extract_value(label, text):
            # Find number (including decimal) after Label
            # Example: "Actual 46.5" or "Actual: 46.5"
            pattern = rf"{label}[:\s]+(\d+\.?\d*)"
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1) if match else None

        result['actual'] = extract_value('Actual', full_text)
        result['forecast'] = extract_value('Forecast', full_text)
        result['previous'] = extract_value('Previous', full_text)

        # Validate results
        required_keys = ['actual', 'forecast', 'previous']
        if all(result.get(k) for k in required_keys):
            return result
        else:
            print(f"Incomplete data parsing. Found: {result}")
            # Print source text being parsed for debugging
            print(f"-> Source Text looked like: '{full_text}'")
            return None

    except Exception as e:
        print(f"General error: {e}")
        if retry_count < max_retries:
            delay = 2.0 * (2 ** retry_count)
            print(f"Retrying in {delay}s...")
            time.sleep(delay)
            return scrape_ism_pmi(retry_count + 1, max_retries)
        else:
            return None

def fetch_fred_data(series_id, series_name):
    """
    Fetch a single FRED economic indicator and return latest 2 data points.

    Args:
        series_id (str): FRED series ID (e.g., 'GDPC1')
        series_name (str): Display name for logging

    Returns:
        dict: {value, prev_value, change_pct, date} or None if failed
    """
    try:
        from pandas_datareader import data as web

        # Fetch last 2 years of data (handles quarterly series)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # ~2 years

        # Fetch data from FRED
        data = web.DataReader(series_id, 'fred', start_date, end_date)

        # Check if we have sufficient data
        if data.empty or len(data) < 2:
            return None

        # Get latest 2 values
        latest = float(data.iloc[-1].iloc[0])
        previous = float(data.iloc[-2].iloc[0])

        # Calculate percentage change
        change_pct = ((latest - previous) / previous) * 100 if previous != 0 else 0.0

        # Get date of latest value
        latest_date = data.index[-1].strftime('%b %Y')

        return {
            'value': latest,
            'prev_value': previous,
            'change_pct': change_pct,
            'date': latest_date
        }

    except Exception:
        # Failed to fetch this series
        return None


def format_fred_value(value, indicator_name):
    """
    Format FRED value based on indicator type.

    Args:
        value (float): Numeric value to format
        indicator_name (str): Indicator name to determine formatting

    Returns:
        str: Formatted value string
    """
    # GDP and monetary aggregates in billions
    if any(keyword in indicator_name for keyword in ['GDP', 'M2', 'Profit', 'Corporate']):
        return f"{value:,.1f}B"

    # Rates, percentages, spreads
    elif any(keyword in indicator_name for keyword in ['Interest Rate', 'Rate', 'Unemployment Rate', 'Unemployment', 'Expectation', 'Capacity Utilization', 'Spread']):
        return f"{value:.2f}%"

    # Price indexes
    elif any(keyword in indicator_name for keyword in ['CPI', 'PPI', 'PCE', 'HICP', 'Index']):
        return f"{value:.2f}"

    # Employment counts (in thousands)
    elif any(keyword in indicator_name for keyword in ['Payrolls', 'Employment', 'Non-farm']):
        return f"{value:,.0f}K"

    # Sales, orders (in millions/billions)
    elif any(keyword in indicator_name for keyword in ['Sales', 'Orders', 'Housing Starts']):
        return f"{value:,.0f}M"

    # VIX volatility
    elif 'VIX' in indicator_name or 'Volatility' in indicator_name:
        return f"{value:.2f}"

    # Default: 2 decimal places with commas
    else:
        return f"{value:,.2f}"


def fetch_world_bank_data(indicator_symbol, indicator_name, countries):
    """
    Fetch World Bank indicator for multiple countries.

    Args:
        indicator_symbol (str): WB indicator code (e.g., 'NY.GDP.MKTP.KD.ZG')
        indicator_name (str): Display name
        countries (list): List of country codes (e.g., ['US', 'CN', 'KR'])

    Returns:
        dict: {country_code: {value, year}, ...} or None if all failed
    """
    try:
        from pandas_datareader import wb

        end_date = datetime.now()
        start_date = end_date - timedelta(days=1095)  # ~3 years

        result = {}

        for country in countries:
            try:
                # Fetch data for this country
                data = wb.download(
                    indicator=indicator_symbol,
                    country=country,
                    start=start_date,
                    end=end_date
                )

                if not data.empty:
                    # Get most recent value
                    latest = data.iloc[-1].iloc[0]
                    year = data.index[-1][1]  # MultiIndex: (country, year)

                    result[country] = {
                        'value': float(latest),
                        'year': year
                    }

            except Exception:
                continue  # Skip this country if it fails

        return result if result else None

    except Exception:
        return None


def fetch_market_index(symbol, name):
    """
    Fetch latest market index data from yfinance.

    Args:
        symbol (str): Index symbol (e.g., '^GSPC')
        name (str): Display name

    Returns:
        dict: {close, change_pct, date} or None if failed
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)

        # Get last 5 days of data
        hist = ticker.history(period='5d')

        if hist.empty or len(hist) < 2:
            return None

        latest = float(hist['Close'].iloc[-1])
        previous = float(hist['Close'].iloc[-2])
        change_pct = ((latest - previous) / previous) * 100
        date = hist.index[-1].strftime('%Y-%m-%d')

        return {
            'close': latest,
            'change_pct': change_pct,
            'date': date
        }

    except Exception:
        return None


def format_wb_value(value, indicator_name):
    """
    Format World Bank value based on indicator type.

    Args:
        value (float): Numeric value
        indicator_name (str): Indicator name to determine formatting

    Returns:
        str: Formatted value string
    """
    # Population in billions
    if any(keyword in indicator_name for keyword in ['Population']):
        return f"{value/1e9:.2f}B"
    # Rates and percentages
    elif any(keyword in indicator_name for keyword in ['Growth Rate', 'Inflation', 'Unemployment Rate', 'Interest Rate', 'Balance']):
        return f"{value:.2f}%"
    else:
        return f"{value:,.2f}"


def fetch_sector_etf_data(symbol, name):
    """
    Fetch sector ETF performance data from yfinance.

    Args:
        symbol (str): ETF symbol (e.g., 'XLK')
        name (str): Display name (e.g., 'Technology')

    Returns:
        dict: {close, change_1d_pct, change_5d_pct, change_1m_pct, date} or None if failed
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='1mo')

        if hist.empty or len(hist) < 2:
            return None

        latest_close = float(hist['Close'].iloc[-1])
        latest_date = hist.index[-1].strftime('%Y-%m-%d')

        # Calculate multi-period changes
        change_1d_pct = 0.0
        change_5d_pct = 0.0
        change_1m_pct = 0.0

        if len(hist) >= 2:
            prev_1d = float(hist['Close'].iloc[-2])
            change_1d_pct = ((latest_close - prev_1d) / prev_1d) * 100

        if len(hist) >= 6:
            prev_5d = float(hist['Close'].iloc[-6])
            change_5d_pct = ((latest_close - prev_5d) / prev_5d) * 100

        if len(hist) >= 21:
            prev_1m = float(hist['Close'].iloc[-21])
            change_1m_pct = ((latest_close - prev_1m) / prev_1m) * 100

        return {
            'close': latest_close,
            'change_1d_pct': change_1d_pct,
            'change_5d_pct': change_5d_pct,
            'change_1m_pct': change_1m_pct,
            'date': latest_date
        }

    except Exception:
        return None


def format_sector_etf_output(etf_data, name, symbol):
    """
    Format sector ETF data into compact single-line output.

    Args:
        etf_data (dict): Data from fetch_sector_etf_data()
        name (str): Display name
        symbol (str): ETF symbol

    Returns:
        str: Formatted single-line output
    """
    if not etf_data:
        return f"- {name} ({symbol}): [Data unavailable]\n"

    line = f"- {name} ({symbol}): ${etf_data['close']:.2f} | "
    line += f"1D: {etf_data['change_1d_pct']:+.2f}% | "
    line += f"5D: {etf_data['change_5d_pct']:+.2f}% | "
    line += f"1M: {etf_data['change_1m_pct']:+.2f}%\n"

    return line


# ==================== ECONOMIC CYCLE HELPER FUNCTIONS ====================

def fetch_ecos_data(stat_code, item_code, cycle, name):
    """
    Fetch Korean Bank (ECOS) economic indicator.

    Args:
        stat_code (str): ECOS statistic code (e.g., '901Y014')
        item_code (str): Item code within statistic
        cycle (str): Data cycle ('D', 'M', 'Q', 'A'/'Y')
        name (str): Display name

    Returns:
        dict: {value, prev_value, change_pct, date} or None if failed
    """
    try:
        api_key = os.getenv('ECOS_API_KEY')
        if not api_key:
            return None

        # Calculate date range (optimized by cycle frequency)
        date_ranges = {'D': 180, 'M': 730, 'Q': 730, 'A': 2190, 'Y': 2190}
        lookback_days = date_ranges.get(cycle, 730)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # Format dates based on cycle
        if cycle == 'Q':
            start_str = start_date.strftime('%Y') + 'Q1'
            end_str = end_date.strftime('%Y') + 'Q4'
        elif cycle == 'M':
            start_str = start_date.strftime('%Y%m')
            end_str = end_date.strftime('%Y%m')
        elif cycle == 'A' or cycle == 'Y':  # Annual/Yearly
            start_str = start_date.strftime('%Y')
            end_str = end_date.strftime('%Y')
        else:  # Daily
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

        # ECOS API endpoint
        url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/100/{stat_code}/{cycle}/{start_str}/{end_str}/{item_code}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Parse response
        if 'StatisticSearch' not in data or 'row' not in data['StatisticSearch']:
            return None

        rows = data['StatisticSearch']['row']

        if len(rows) < 2:
            return None

        # Get latest 2 values
        latest = float(rows[-1]['DATA_VALUE'])
        previous = float(rows[-2]['DATA_VALUE'])

        change_pct = ((latest - previous) / previous) * 100 if previous != 0 else 0.0

        date_str = rows[-1]['TIME']
        # Format date display
        if cycle == 'Q':
            date_display = date_str  # Already in YYYYQ# format
        elif cycle == 'M':
            date_display = datetime.strptime(date_str, '%Y%m').strftime('%b %Y')
        elif cycle == 'A' or cycle == 'Y':  # Annual/Yearly
            date_display = date_str
        else:
            date_display = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')

        return {
            'value': latest,
            'prev_value': previous,
            'change_pct': change_pct,
            'date': date_display
        }

    except Exception:
        return None


def fetch_ecos_data_aggregated(stat_code, item_code_base, item_codes, cycle, name):
    """
    Fetch and aggregate multiple ECOS item codes (e.g., Corporate Debt categories).

    This function is used when an ECOS statistic returns multiple rows per time period
    (e.g., BDDF1 returns separate values for ITEM_CODE2=A and B) that need to be summed.

    Args:
        stat_code (str): ECOS statistic code (e.g., '131Y017')
        item_code_base (str): Base item code (e.g., 'BDDF1') for ITEM_CODE1
        item_codes (list): List of sub-item codes (e.g., ['A', 'B']) for ITEM_CODE2
        cycle (str): Data cycle ('D', 'M', 'Q', 'Y')
        name (str): Display name for error messages

    Returns:
        dict: {value, prev_value, change_pct, date} or None if any category fails
    """
    try:
        api_key = os.getenv('ECOS_API_KEY')
        if not api_key:
            return None

        # Calculate date range with optimized lookback
        date_ranges = {'D': 180, 'M': 730, 'Q': 730, 'Y': 2190}
        lookback_days = date_ranges.get(cycle, 730)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # Format dates based on cycle
        if cycle == 'Q':
            start_str = start_date.strftime('%Y') + 'Q1'
            end_str = end_date.strftime('%Y') + 'Q4'
        elif cycle == 'M':
            start_str = start_date.strftime('%Y%m')
            end_str = end_date.strftime('%Y%m')
        elif cycle == 'Y':
            start_str = start_date.strftime('%Y')
            end_str = end_date.strftime('%Y')
        else:  # Daily
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

        # Fetch data for each item code and aggregate
        aggregated_latest = 0.0
        aggregated_previous = 0.0
        latest_date = None

        for item_code in item_codes:
            # Two-level item code structure: base item code + sub-item code
            url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/100/{stat_code}/{cycle}/{start_str}/{end_str}/{item_code_base}/{item_code}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse response
            if 'StatisticSearch' not in data or 'row' not in data['StatisticSearch']:
                return None  # Fail if any category is missing

            rows = data['StatisticSearch']['row']

            if len(rows) < 2:
                return None  # Need at least 2 data points

            # Aggregate values
            aggregated_latest += float(rows[-1]['DATA_VALUE'])
            aggregated_previous += float(rows[-2]['DATA_VALUE'])

            # Use date from first successful fetch
            if latest_date is None:
                latest_date = rows[-1]['TIME']

        # Calculate change percentage
        change_pct = ((aggregated_latest - aggregated_previous) / aggregated_previous) * 100 if aggregated_previous != 0 else 0.0

        # Format date display
        if cycle == 'Q':
            date_display = latest_date
        elif cycle == 'M':
            date_display = datetime.strptime(latest_date, '%Y%m').strftime('%b %Y')
        elif cycle == 'Y':
            date_display = latest_date
        else:
            date_display = datetime.strptime(latest_date, '%Y%m%d').strftime('%Y-%m-%d')

        return {
            'value': aggregated_latest,
            'prev_value': aggregated_previous,
            'change_pct': change_pct,
            'date': date_display
        }

    except Exception:
        return None


def fetch_ecos_data_timeseries(stat_code, item_code, cycle, name, data_points=None):
    """
    Fetch ECOS time series data with configurable point count.

    Args:
        stat_code (str): ECOS statistic code (e.g., '901Y009')
        item_code (str): Item code within statistic (e.g., '0' or 'I61BC/I28A')
        cycle (str): Data cycle ('D', 'M', 'Q', 'A')
        name (str): Display name for logging
        data_points (int, optional): Number of data points to return
                                     Defaults: 24 (M/Q), 10 (A)

    Returns:
        dict: {
            'values': [float, ...],      # Time series values
            'dates': [str, ...],         # Formatted dates
            'latest': float,             # Most recent value
            'trend': str,                # 'rising', 'falling', 'stable'
            'change_pct': float,         # Latest vs previous %
            'min': float,                # Minimum in series
            'max': float,                # Maximum in series
            'avg': float                 # Average of series
        } or None if failed
    """
    try:
        api_key = os.getenv('ECOS_API_KEY')
        if not api_key:
            return None

        # Default data points based on cycle
        if data_points is None:
            data_points = 10 if cycle == 'A' else 24

        # Calculate date range (optimized by cycle frequency)
        date_ranges = {'D': 180, 'M': 730, 'Q': 730, 'A': 3650}  # Updated A to 10 years
        lookback_days = date_ranges.get(cycle, 730)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # Format dates based on cycle
        if cycle == 'Q':
            start_str = start_date.strftime('%Y') + 'Q1'
            end_str = end_date.strftime('%Y') + 'Q4'
        elif cycle == 'M':
            start_str = start_date.strftime('%Y%m')
            end_str = end_date.strftime('%Y%m')
        elif cycle == 'A':
            start_str = start_date.strftime('%Y')
            end_str = end_date.strftime('%Y')
        else:  # Daily
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

        # ECOS API endpoint (fetch up to 100 records)
        url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/100/{stat_code}/{cycle}/{start_str}/{end_str}/{item_code}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Parse response
        if 'StatisticSearch' not in data or 'row' not in data['StatisticSearch']:
            return None

        rows = data['StatisticSearch']['row']

        if len(rows) < 2:
            return None

        # Slice to get last N points (or all if fewer)
        if len(rows) > data_points:
            rows = rows[-data_points:]

        # Extract time series
        values = [float(row['DATA_VALUE']) for row in rows]

        # Format dates
        dates = []
        for row in rows:
            date_str = row['TIME']
            if cycle == 'Q':
                dates.append(date_str)  # Already in YYYYQ# format
            elif cycle == 'M':
                dates.append(datetime.strptime(date_str, '%Y%m').strftime('%b %Y'))
            elif cycle == 'A':
                dates.append(date_str)
            else:  # Daily
                dates.append(datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'))

        # Calculate statistics
        latest = values[-1]
        prev = values[-2] if len(values) >= 2 else latest
        change_pct = ((latest - prev) / prev) * 100 if prev != 0 else 0.0

        # Trend analysis (compare latest to average with 2% threshold)
        avg = sum(values) / len(values)
        if latest > avg * 1.02:
            trend = 'rising'
        elif latest < avg * 0.98:
            trend = 'falling'
        else:
            trend = 'stable'

        return {
            'values': values,
            'dates': dates,
            'latest': latest,
            'trend': trend,
            'change_pct': change_pct,
            'min': min(values),
            'max': max(values),
            'avg': avg
        }

    except Exception:
        return None


def fetch_ecos_data_multi_item(stat_code, item_codes_config, cycle, name, data_points=None):
    """
    Fetch ECOS data for multiple item codes (returns separate entries).

    Args:
        stat_code (str): ECOS statistic code
        item_codes_config (list): List of dicts with 'code' and 'name'
                                  e.g., [{'code': 'AA/99988', 'name': '전산업'},
                                         {'code': 'AM/99988', 'name': '제조업'}]
        cycle (str): Data cycle ('D', 'M', 'Q', 'A')
        name (str): Base display name
        data_points (int, optional): Number of data points to return

    Returns:
        dict: {
            'item_name_1': {...},  # Same structure as fetch_ecos_data_timeseries
            'item_name_2': {...},
            ...
        } or None if <50% succeed
    """
    try:
        results = {}
        failed_items = []

        for item_config in item_codes_config:
            item_code = item_config['code']
            item_name = f"{name} - {item_config['name']}"

            # Fetch data for this item code
            item_data = fetch_ecos_data_timeseries(
                stat_code,
                item_code,
                cycle,
                item_name,
                data_points
            )

            if item_data:
                results[item_name] = item_data
            else:
                failed_items.append(item_name)

            # Rate limiting between item codes
            time.sleep(0.2)

        # Return partial results if at least 50% succeeded
        if len(results) >= len(item_codes_config) // 2:
            return results
        else:
            return None  # Too many failures

    except Exception:
        return None


def format_ecos_value(value, indicator_name):
    """
    Format ECOS value based on indicator type.

    Args:
        value (float): Numeric value
        indicator_name (str): Indicator name

    Returns:
        str: Formatted value string
    """
    # GDP values
    if 'GDP' in indicator_name or 'gdp' in indicator_name.lower():
        # ECOS 902Y016 returns GDP in million dollars
        if value > 100000:  # Likely in million dollars (e.g., 1,844,800.9)
            return f"${value:,.1f}M"  # e.g., $1,844,800.9M
        else:  # Likely in trillions of KRW
            return f"{value:,.1f}trillion KRW"
    # Price indexes (CPI/PPI)
    elif 'CPI' in indicator_name or 'PPI' in indicator_name or '물가' in indicator_name:
        return f"{value:.2f}"
    # Sentiment/confidence indexes (0-200 scale)
    elif '심리' in indicator_name or 'BSI' in indicator_name or 'CSI' in indicator_name or '경기실사' in indicator_name:
        return f"{value:.1f}"
    # Unemployment
    elif '실업' in indicator_name:
        if '실업률' in indicator_name:
            return f"{value:.1f}%"
        else:  # 실업자 count (in thousands)
            return f"{value:,.0f}thousand"
    # Debt values in trillions of KRW
    elif '부채' in indicator_name or 'debt' in indicator_name.lower():
        return f"{value:,.1f}trillion KRW"
    # Money supply in trillions of KRW
    elif '통화량' in indicator_name or 'money supply' in indicator_name.lower():
        return f"{value:,.1f}trillion KRW"
    # Interest rates as percentages
    elif '금리' in indicator_name or 'rate' in indicator_name.lower():
        return f"{value:.2f}%"
    else:
        return f"{value:,.2f}"


def format_timeseries_output(data, indicator_name):
    """
    Format time series data for economic cycle dashboard.

    Args:
        data (dict): Time series data from fetch_ecos_data_timeseries
        indicator_name (str): Display name

    Returns:
        str: Formatted multi-line output (4 lines per indicator)
    """
    # Format values based on indicator type
    latest_str = format_ecos_value(data['latest'], indicator_name)
    min_str = format_ecos_value(data['min'], indicator_name)
    max_str = format_ecos_value(data['max'], indicator_name)
    avg_str = format_ecos_value(data['avg'], indicator_name)

    # Build output
    output = f"- {indicator_name}:\n"
    output += f"  Latest: {latest_str} ({data['dates'][-1]}) | "
    output += f"Trend: {data['trend']} | Δ: {data['change_pct']:+.2f}%\n"
    output += f"  Range: {min_str} - {max_str} | Avg: {avg_str}\n"

    # Time series data (compact format)
    # Show every 3rd point for monthly (24 -> 8 points), all for annual
    if len(data['values']) > 12:
        step = 3
        display_values = [format_ecos_value(data['values'][i], indicator_name)
                         for i in range(0, len(data['values']), step)]
        display_dates = [data['dates'][i] for i in range(0, len(data['dates']), step)]
    else:
        display_values = [format_ecos_value(v, indicator_name) for v in data['values']]
        display_dates = data['dates']

    output += f"  Series: {', '.join(display_values)}\n"
    output += f"  Dates:  {', '.join(display_dates)}\n"

    return output


def fetch_commodity_ratio(numerator_symbol, denominator_symbol, ratio_name):
    """
    Fetch commodity ratio (e.g., Copper/Gold) from yfinance.

    Args:
        numerator_symbol (str): Numerator commodity symbol (e.g., 'HG=F')
        denominator_symbol (str): Denominator commodity symbol (e.g., 'GC=F')
        ratio_name (str): Display name

    Returns:
        dict: {ratio, change_pct, date} or None if failed
    """
    try:
        # Input validation
        if not numerator_symbol or not denominator_symbol:
            print(f"[Error] {ratio_name}: Invalid ticker symbols - numerator='{numerator_symbol}', denominator='{denominator_symbol}'")
            return None

        import yfinance as yf

        # Fetch both commodities (using 1mo to handle weekends/holidays)
        num_ticker = yf.Ticker(numerator_symbol)
        den_ticker = yf.Ticker(denominator_symbol)

        num_hist = num_ticker.history(period='1mo')
        den_hist = den_ticker.history(period='1mo')

        # Detailed data validation with diagnostics
        if num_hist.empty:
            print(f"[Error] {ratio_name}: No data available for numerator '{numerator_symbol}'")
            return None

        if den_hist.empty:
            print(f"[Error] {ratio_name}: No data available for denominator '{denominator_symbol}'")
            return None

        if len(num_hist) < 2:
            print(f"[Error] {ratio_name}: Insufficient data for numerator '{numerator_symbol}' - only {len(num_hist)} data point(s), need at least 2")
            return None

        if len(den_hist) < 2:
            print(f"[Error] {ratio_name}: Insufficient data for denominator '{denominator_symbol}' - only {len(den_hist)} data point(s), need at least 2")
            return None

        # Calculate ratios
        latest_num = float(num_hist['Close'].iloc[-1])
        latest_den = float(den_hist['Close'].iloc[-1])

        prev_num = float(num_hist['Close'].iloc[-2])
        prev_den = float(den_hist['Close'].iloc[-2])

        # Check for zero denominator
        if latest_den == 0 or prev_den == 0:
            print(f"[Error] {ratio_name}: Division by zero - denominator '{denominator_symbol}' has zero value")
            return None

        latest_ratio = latest_num / latest_den
        prev_ratio = prev_num / prev_den

        change_pct = ((latest_ratio - prev_ratio) / prev_ratio) * 100

        date = num_hist.index[-1].strftime('%Y-%m-%d')

        return {
            'ratio': latest_ratio,
            'change_pct': change_pct,
            'date': date
        }

    except Exception as e:
        print(f"[Error] Commodity ratio '{ratio_name}' ({numerator_symbol}/{denominator_symbol}) fetch failed: {str(e)[:150]}")
        return None


def fetch_fear_greed_index():
    """
    Fetch CNN Fear & Greed Index.

    Returns:
        dict: {value, description, last_update} or None if failed
    """
    try:
        import fear_and_greed

        fgi = fear_and_greed.get()

        return {
            'value': fgi.value,
            'description': fgi.description,
            'last_update': fgi.last_update
        }

    except Exception:
        return None


def async_scrape_shiller_pe():
    """
    Scrape Shiller PE from multpl.com using AsyncChromiumLoader logic.
    Refactored to robustly parse value by decomposing other tags first.
    """
    try:
        url = "https://www.multpl.com/shiller-pe"

        # Run async loader
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html_content = loop.run_until_complete(
            async_load_with_retry(url, ['.advertisement', '.sidebar'])
        )
        loop.close()

        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        current_div = soup.find('div', id='current')

        if not current_div:
            return None

        # --- Parsing logic (same as S&P 500 PE) ---

        # 1. Extract date and remove tag
        date_elem = current_div.find('div', id='timestamp')
        date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%Y-%m-%d')
        if date_elem:
            date_elem.decompose()

        # 2. Extract change, remove line breaks, remove tag
        change_elem = current_div.find('span', class_=['change', 'pos', 'neg'])
        if change_elem:
            # Replace line breaks (\n) with spaces to make it a single line
            change = change_elem.get_text(strip=True).replace('\n', ' ')
            change_elem.decompose()
        else:
            change = "N/A"

        # 3. Remove title tag (<b>) to prevent number interference
        title_elem = current_div.find('b')
        if title_elem:
            title_elem.decompose()

        # 4. Extract value (parse from remaining text)
        value_text = current_div.get_text(strip=True)
        value_match = re.search(r'[\d,]+\.?\d*', value_text)
        
        if not value_match:
            return None

        value = float(value_match.group().replace(',', ''))

        return {
            'value': value,
            'change': change,
            'date': date
        }

    except Exception as e:
        print(f"Error in async_scrape_shiller_pe: {e}")
        return None
    

def async_scrape_sp500_pe():
    """
    Scrape S&P 500 PE-Ratio from multpl.com using AsyncChromiumLoader.

    Returns:
        dict: {value, change, date} or None if failed
    """
    try:
        url = "https://www.multpl.com/s-p-500-pe-ratio"

        # 1. Run async loader (in synchronous environment)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html_content = loop.run_until_complete(
            async_load_with_retry(url, ['.advertisement', '.sidebar'])
        )
        loop.close()

        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # 2. Find main container
        current_div = soup.find('div', id='current')
        if not current_div:
            return None

        # --- [Core fix] Change parsing order and remove noise tags ---

        # 3. Extract date and remove tag
        date_elem = current_div.find('div', id='timestamp')
        date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%Y-%m-%d')
        if date_elem:
            date_elem.decompose()  # Remove from HTML tree to prevent interference

        # 4. Extract price change and remove tags
        # Find elements with class change, pos, or neg
        change_elem = current_div.find('span', class_=['change', 'pos', 'neg'])
        change = change_elem.get_text(strip=True) if change_elem else "N/A"
        if change_elem:
            change_elem.decompose() # Remove from HTML tree

        # 5. Remove title (S&P 500 text) tags
        # The <b> tag contains "S&P 500" numbers, so it must be removed first
        title_elem = current_div.find('b')
        if title_elem:
            title_elem.decompose()

        # 6. Extract value (remaining text is pure value only)
        value_text = current_div.get_text(strip=True)
        
        # Extract float using regex
        value_match = re.search(r'[\d,]+\.?\d*', value_text)
        
        if not value_match:
            return None

        value = float(value_match.group().replace(',', ''))

        return {
            'value': value,
            'change': change,
            'date': date
        }

    except Exception as e:
        print(f"Scraping failed: {e}")
        return None


# ==================== FOMC DOCUMENT SCRAPING ====================

def fetch_page(url):
    """Helper function to fetch URL content"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # [Important] Force UTF-8 to prevent special character corruption
        response.encoding = 'utf-8'
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[Error] {url} connection failed: {e}")
        return None

def extract_content(url):
    """Function to extract title and body from URL"""
    soup = fetch_page(url)
    if not soup:
        return None

    # 1. Extract title
    title = soup.find('title').get_text(strip=True)
    article_section = soup.find('div', id='article')

    if article_section:
        header = article_section.find(['h2', 'h3', 'h1'])
        if header:
            # Use separator as title may have line breaks
            title = header.get_text(separator=' ', strip=True)

    # 2. Extract body
    content_text = ""
    if article_section:
        paragraphs = article_section.find_all('p')
        # [Modified] Add separator='\n' to insert line break when <br> or tag ends
        text_list = []
        for p in paragraphs:
            # Insert line break between tags when extracting text
            text = p.get_text(separator='\n', strip=True)
            if text:
                text_list.append(text)

        # Add two line breaks (\n\n) between paragraphs (p)
        content_text = "\n\n".join(text_list)
    else:
        # Edge case where id='article' doesn't exist
        content_text = soup.body.get_text(separator='\n', strip=True)

    return title, content_text

def get_latest_fomc_documents():
    """
    Fetch latest FOMC Minutes and Statement from Federal Reserve website.

    Returns:
        dict: {
            'statement': {'date', 'title', 'url', 'content'},
            'minutes': {'date', 'title', 'url', 'content'}
        } or None if failed
    """
    base_url = "https://www.federalreserve.gov"
    calendar_url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

    print("Fetching Calendar Page...")
    soup_cal = fetch_page(calendar_url)
    if not soup_cal:
        return None

    docs_found = {
        'minutes': [],
        'statement': []
    }

    # Regular expression
    pattern_minutes = re.compile(r'fomcminutes(\d{8})\.htm')
    pattern_statement = re.compile(r'monetary(\d{8})[a-z]?\.htm')

    for link in soup_cal.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)

        # 1. Minutes
        match_min = pattern_minutes.search(href)
        if match_min:
            docs_found['minutes'].append({
                'date': match_min.group(1),
                'url': full_url,
                'type': 'Minutes'
            })
            continue

        # 2. Statement
        match_stmt = pattern_statement.search(href)
        if match_stmt and 'htm' in href:
            docs_found['statement'].append({
                'date': match_stmt.group(1),
                'url': full_url,
                'type': 'Statement'
            })

    results = {}

    for doc_type in ['statement', 'minutes']:
        doc_list = docs_found[doc_type]
        if not doc_list:
            print(f"[{doc_type}] link not found.")
            continue

        # Sort by date descending
        latest_doc = sorted(doc_list, key=lambda x: x['date'], reverse=True)[0]

        print(f"\n>> latest {latest_doc['type']} extracting... (date: {latest_doc['date']})")

        title, content = extract_content(latest_doc['url'])

        results[doc_type] = {
            "date": latest_doc['date'],
            "title": title,
            "url": latest_doc['url'],
            "content": content
        }

    return results


# ==================== MAIN TOOLS ====================

@tool
def get_global_environment(ticker: str) -> str:
    """
    Global Economic Environment Analysis: Collects key global macroeconomic indicators from 6 sources.
    1) ISM Manufacturing PMI (Manufacturing Business Index)
    2) World Bank Data (World Bank Macro Indicators - 5 Countries)
    3) FRED Major Indicators (Key Interest Rates, Liquidity, Exchange Rates)
    4) FRED OECD Interest Rates (Eurozone, Japan Rates)
    5) Market Indices (4 Major Global Indices)
    6) FRED Market Analysis (Credit Risk, Commodities, Sentiment Indices)

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str: Summary of global macroeconomic indicators from 6 sources
    """
    # 1. Initialize
    is_korean_stock = ticker.isdigit()

    summary = f"--- GLOBAL ECONOMIC ENVIRONMENT ({ticker}) ---\n"
    summary += f"Stock Type: {'Korean (KS)' if is_korean_stock else 'US'}\n"
    summary += f"Data Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    failed_sources = []
    total_indicators = 0
    successful_indicators = 0

    # 2. SOURCE 1: ISM Manufacturing PMI
    summary += "=== 1. ISM MANUFACTURING PMI ===\n"

    try:
        ism_data = scrape_ism_pmi()

        if ism_data:
            summary += f"Latest: {ism_data.get('date', 'N/A')}\n"
            summary += f"Actual: {ism_data.get('actual', 'N/A')} | "
            summary += f"Forecast: {ism_data.get('forecast', 'N/A')} | "
            summary += f"Previous: {ism_data.get('previous', 'N/A')}\n"
            summary += "(Note: <50 = contraction)\n\n"
        else:
            summary += "[!] ISM PMI data collection failed\n\n"
            failed_sources.append("ISM PMI")
    except Exception as e:
        summary += f"[!] ISM PMI failed: {str(e)[:100]}\n\n"
        failed_sources.append("ISM PMI")

    time.sleep(0.5)

    # 3. SOURCE 2: World Bank Data
    summary += "=== 2. WORLD BANK INDICATORS (5 Countries) ===\n\n"

    try:
        from .macro_config import (
            WORLD_BANK_INDICATORS,
            COUNTRY_CODES,
            KOREA_PRIORITY_COUNTRIES,
            US_PRIORITY_COUNTRIES
        )

        priority_countries = KOREA_PRIORITY_COUNTRIES if is_korean_stock else US_PRIORITY_COUNTRIES

        for indicator in WORLD_BANK_INDICATORS:
            total_indicators += 5  # 5 countries per indicator

            wb_data = fetch_world_bank_data(
                indicator['symbol'],
                indicator['name'],
                priority_countries
            )

            if wb_data:
                summary += f"[{indicator['name']}]\n"

                for country_code in priority_countries:
                    if country_code in wb_data:
                        country_name = COUNTRY_CODES.get(country_code, country_code)
                        val_str = format_wb_value(wb_data[country_code]['value'], indicator['name'])
                        year = wb_data[country_code]['year']

                        summary += f"- {country_name}: {val_str} ({year})\n"
                        successful_indicators += 1

                summary += "\n"

    except Exception as e:
        summary += f"[!] World Bank data collection failed: {str(e)[:150]}\n\n"
        failed_sources.append("World Bank")

    time.sleep(0.5)

    # 4. SOURCE 3: FRED Major Indicators
    summary += "=== 3. FRED MAJOR INDICATORS ===\n\n"

    try:
        from .macro_config import GLOBAL_FRED_INDICATORS

        # Group by category
        by_category = {}
        for ind in GLOBAL_FRED_INDICATORS:
            cat = ind['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(ind)

        for category, indicators in by_category.items():
            summary += f"[{category}]\n"

            for ind in indicators:
                total_indicators += 1
                fred_data = fetch_fred_data(ind['series_id'], ind['name'])

                if fred_data:
                    successful_indicators += 1
                    val_str = format_fred_value(fred_data['value'], ind['name'])

                    summary += f"- {ind['name']} ({ind['series_id']}): "
                    summary += f"{val_str} ({fred_data['date']}) | "
                    summary += f"Δ: {fred_data['change_pct']:+.2f}%\n"

            summary += "\n"

    except Exception as e:
        summary += f"[!] FRED data collection failed: {str(e)[:150]}\n\n"
        failed_sources.append("FRED")

    time.sleep(0.5)

    # 5. SOURCE 4: Market Indices
    summary += "=== 4. GLOBAL MARKET INDICES ===\n"

    try:
        from .macro_config import MARKET_INDICES

        for index in MARKET_INDICES:
            total_indicators += 1

            index_data = fetch_market_index(index['symbol'], index['name'])

            if index_data:
                successful_indicators += 1
                summary += f"- {index['name']} ({index['symbol']}): "
                summary += f"{index_data['close']:,.2f} "
                summary += f"({index_data['change_pct']:+.2f}%) "
                summary += f"[{index_data['date']}]\n"

        summary += "\n"

    except Exception as e:
        summary += f"[!] Market Indices collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("Market Indices")

    time.sleep(0.5)

    # 6. SUMMARY
    summary += "=== SUMMARY ===\n"

    sources_collected = 6 - len(failed_sources)
    summary += f"Data Sources Collected: {sources_collected}/6"
    if sources_collected == 6:
        summary += " ✓"
    summary += "\n"

    if total_indicators > 0:
        summary += f"Indicators Collected: {successful_indicators}/{total_indicators} "
        summary += f"({(successful_indicators/total_indicators)*100:.1f}%)\n"

    if failed_sources:
        summary += f"Failed Sources: {', '.join(failed_sources)}\n"

    summary += "\nNote: Data is based on the latest publicly available values from each source.\n"

    return summary


@tool
def get_economic_indicator(ticker: str) -> str:
    """
    Macroeconomic Data Collection: Collects key economic indicators from 3 sources.
    1) ISM Manufacturing PMI (Manufacturing Business Index)
    2) Fear & Greed Index (Market Sentiment Index)
    3) Economic Data (FRED + ECOS - 27 indicators)

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')
                     Numeric tickers (Korea) prioritize OECD Korea data,
                     Letter tickers (US) prioritize US data

    Returns:
        str: Summary of macroeconomic indicators from 3 sources (formatted by section)
    """

    # === 1. Initialize ===
    is_korean_stock = ticker.isdigit()

    summary = f"--- MACROECONOMIC DATA ({ticker}) ---\n"
    summary += f"Stock Type: {'Korean (KS)' if is_korean_stock else 'US'}\n"
    summary += f"Data Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    failed_sources = []
    failed_indicators = []
    successful_indicators = 0

    # === 2. SOURCE 1: ISM Manufacturing PMI ===
    summary += "=== 1. ISM MANUFACTURING PMI (investing.com) ===\n"

    try:
        ism_data = scrape_ism_pmi()

        if ism_data:
            summary += f"Latest Release: {ism_data.get('date', 'N/A')}\n"
            summary += f"Actual: {ism_data.get('actual', 'N/A')} | "
            summary += f"Forecast: {ism_data.get('forecast', 'N/A')} | "
            summary += f"Previous: {ism_data.get('previous', 'N/A')}\n"
            summary += "(Note: <50 indicates contraction)\n\n"
        else:
            summary += "[!] ISM PMI data collection failed (page parsing error or access restriction)\n\n"
            failed_sources.append("ISM PMI")

    except Exception as e:
        summary += f"[!] ISM PMI collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("ISM PMI")

    time.sleep(0.5)  # Rate limiting

    # === 3. SOURCE 2: Fear & Greed Index ===
    summary += "=== 2. FEAR & GREED INDEX (Market-Wide) ===\n"

    try:
        import fear_and_greed
        fgi = fear_and_greed.get()

        summary += f"Current Index: {fgi.value}/100 - {fgi.description}\n"
        summary += f"Last Updated: {fgi.last_update}\n"
        summary += "(Note: Market-wide index, independent of individual stocks)\n\n"

    except Exception as e:
        summary += f"[!] Fear & Greed Index collection failed: {str(e)[:100]}\n\n"
        failed_sources.append("Fear & Greed")

    time.sleep(0.5)  # Rate limiting

    # === 4. SOURCE 3: Economic Data (27 Indicators from FRED + ECOS) ===
    summary += "=== 3. ECONOMIC DATA (27 Indicators) ===\n\n"

    try:
        from .macro_config import FRED_INDICATORS, KOREA_PRIORITY_CATEGORIES, US_PRIORITY_CATEGORIES

        # Determine category priority based on stock type
        if is_korean_stock:
            priority_categories = KOREA_PRIORITY_CATEGORIES
        else:
            priority_categories = US_PRIORITY_CATEGORIES

        # Group indicators by category
        by_category = {}
        for indicator in FRED_INDICATORS:
            cat = indicator['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(indicator)

        # Fetch and format data by category
        for category in priority_categories:
            if category not in by_category:
                continue

            # Category header
            category_indicators = by_category[category]
            summary += f"[Category: {category}]\n"

            # Fetch each indicator in this category
            for indicator in category_indicators:
                # Check source type (default to FRED for backward compatibility)
                source = indicator.get('source', 'FRED')

                if source == 'ECOS':
                    # Fetch from ECOS API
                    ecos_data = fetch_ecos_data(
                        indicator['stat_code'],
                        indicator['item_code'],
                        indicator['cycle'],
                        indicator['name']
                    )

                    if ecos_data:
                        successful_indicators += 1

                        # Format values
                        val_str = format_ecos_value(ecos_data['value'], indicator['name'])
                        prev_str = format_ecos_value(ecos_data['prev_value'], indicator['name'])

                        # Build output line
                        summary += f"- {indicator['name']}: "
                        summary += f"{val_str} ({ecos_data['date']}) | "
                        summary += f"Prev: {prev_str} | "
                        summary += f"Δ: {ecos_data['change_pct']:+.2f}%\n"
                    else:
                        failed_indicators.append(f"{indicator['name']} (ECOS)")

                else:  # FRED (default)
                    fred_data = fetch_fred_data(indicator['series_id'], indicator['name'])

                    if fred_data:
                        successful_indicators += 1

                        # Format values
                        val_str = format_fred_value(fred_data['value'], indicator['name'])
                        prev_str = format_fred_value(fred_data['prev_value'], indicator['name'])

                        # Build output line
                        summary += f"- {indicator['name']} ({indicator['series_id']}): "
                        summary += f"{val_str} ({fred_data['date']}) | "
                        summary += f"Prev: {prev_str} | "
                        summary += f"Δ: {fred_data['change_pct']:+.2f}%\n"
                    else:
                        # Failed to fetch this indicator
                        failed_indicators.append(f"{indicator['name']} ({indicator['series_id']})")

            summary += "\n"

    except Exception as e:
        summary += f"[!] FRED data collection error: {str(e)[:150]}\n\n"
        failed_sources.append("FRED")

    # === 4. Summary ===
    summary += "=== SUMMARY ===\n"

    # Count total sources (3 sources: ISM, F&G, FRED)
    unique_failed = list(set(failed_sources))  # Deduplicate
    sources_collected = 3 - len(unique_failed)
    summary += f"Data Sources Collected: {sources_collected}/3"
    if sources_collected == 3:
        summary += " ✓"
    summary += "\n"

    summary += f"Economic Indicators Collected: {successful_indicators}/27\n"

    if unique_failed:
        summary += f"Failed Sources: {', '.join(unique_failed)}\n"

    if failed_indicators:
        summary += f"Failed FRED Series ({len(failed_indicators)}):\n"
        # Show first 10 failures
        for failure in failed_indicators[:10]:
            summary += f"  - {failure}\n"
        if len(failed_indicators) > 10:
            summary += f"  ... and {len(failed_indicators) - 10} more\n"

    summary += "\nNote: Based on the latest publicly available values at the time of data collection.\n"

    return summary


@tool
def get_policy_environment(ticker: str) -> str:
    """
    Policy & Sector Environment Analysis: Collects FRED policy indicators, social/demographic trends, and sector impact.

    3 sections:
    1) Policy Info & Impact (17 FRED indicators: monetary policy, fiscal policy, market impact, forward indicators, housing/household)
    2) Social & Demographic Trends (8 WB + FRED indicators: population, labor market, consumption)
    3) Sector Impact (4 sector ETFs via yfinance: technology, energy, healthcare, consumer staples)

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str: Token-optimized policy/sector environment analysis (~2,200 tokens)
    """
    # 1. Initialize
    is_korean_stock = ticker.isdigit()
    summary = f"--- POLICY & SECTOR ENVIRONMENT ({ticker}) ---\n"
    summary += f"Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    failed_indicators = []
    total_indicators = 0
    successful_indicators = 0

    # 2. Load config
    from .macro_config import POLICY_ENVIRONMENT_CONFIG

    # 3. SECTION 1: Policy Info & Impact Analysis
    summary += "=== 1. POLICY INFO & IMPACT ANALYSIS ===\n\n"

    try:
        section1 = POLICY_ENVIRONMENT_CONFIG['section_1_policy_info']

        for subsection_key, subsection_data in section1['subsections'].items():
            subsection_name = subsection_data['display_name']
            indicators = subsection_data['indicators']

            summary += f"[{subsection_name} - {len(indicators)} indicators]\n"

            for ind in indicators:
                total_indicators += 1
                fred_data = fetch_fred_data(ind['series_id'], ind['name'])

                if fred_data:
                    successful_indicators += 1
                    val_str = format_fred_value(fred_data['value'], ind['name'])
                    prev_str = format_fred_value(fred_data['prev_value'], ind['name'])

                    summary += f"- {ind['name']} ({ind['series_id']}): "
                    summary += f"{val_str} ({fred_data['date']}) | "
                    summary += f"Prev: {prev_str} | Δ: {fred_data['change_pct']:+.2f}%\n"
                else:
                    failed_indicators.append(f"{ind['name']} ({ind['series_id']})")

            summary += "\n"
            time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Section 1 failed: {str(e)[:100]}\n\n"

    # 4. SECTION 2: Social & Demographic Trends
    summary += "=== 2. SOCIAL & DEMOGRAPHIC TRENDS ===\n\n"

    try:
        section2 = POLICY_ENVIRONMENT_CONFIG['section_2_social_demographic']

        for subsection_key, subsection_data in section2['subsections'].items():
            subsection_name = subsection_data['display_name']
            indicators = subsection_data['indicators']

            summary += f"[{subsection_name}]\n"

            for ind in indicators:
                total_indicators += 1

                # Handle mixed sources
                if ind.get('source') == 'WorldBank':
                    wb_data = fetch_world_bank_data(
                        ind['symbol'],
                        ind['name'],
                        ind['countries']
                    )

                    if wb_data:
                        for country_code, data in wb_data.items():
                            successful_indicators += 1
                            val_str = format_wb_value(data['value'], ind['name'])
                            summary += f"- {ind['name']}: {val_str} ({data['year']})\n"
                    else:
                        failed_indicators.append(f"{ind['name']} ({ind['symbol']})")

                else:  # FRED
                    fred_data = fetch_fred_data(ind['series_id'], ind['name'])

                    if fred_data:
                        successful_indicators += 1
                        val_str = format_fred_value(fred_data['value'], ind['name'])
                        prev_str = format_fred_value(fred_data['prev_value'], ind['name'])

                        summary += f"- {ind['name']} ({ind['series_id']}): "
                        summary += f"{val_str} ({fred_data['date']}) | "
                        summary += f"Prev: {prev_str} | Δ: {fred_data['change_pct']:+.2f}%\n"
                    else:
                        failed_indicators.append(f"{ind['name']} ({ind['series_id']})")

            summary += "\n"
            time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Section 2 failed: {str(e)[:100]}\n\n"

    # 5. SECTION 3: Sector Impact Analysis
    summary += "=== 3. SECTOR IMPACT ANALYSIS ===\n\n"

    try:
        section3 = POLICY_ENVIRONMENT_CONFIG['section_3_sector_impact']
        etfs = section3['etfs']

        summary += f"[{len(etfs)} Sector ETFs]\n"

        for etf in etfs:
            total_indicators += 1

            etf_data = fetch_sector_etf_data(etf['symbol'], etf['name'])

            if etf_data:
                successful_indicators += 1
                summary += format_sector_etf_output(etf_data, etf['name'], etf['symbol'])
            else:
                failed_indicators.append(f"{etf['name']} ({etf['symbol']})")
                summary += f"- {etf['name']} ({etf['symbol']}): [Data unavailable]\n"

            time.sleep(0.3)

        summary += "\n"

    except Exception as e:
        summary += f"[!] Section 3 failed: {str(e)[:100]}\n\n"

    # 6. Summary
    summary += "=== SUMMARY ===\n"

    if total_indicators > 0:
        success_rate = (successful_indicators / total_indicators) * 100
        summary += f"Indicators: {successful_indicators}/{total_indicators} ({success_rate:.1f}%)\n"

    if failed_indicators and len(failed_indicators) <= 10:
        summary += f"Failed: {', '.join(failed_indicators)}\n"
    elif failed_indicators:
        summary += f"Failed: {len(failed_indicators)} indicators\n"

    return summary


@tool
def get_economic_cycle(ticker: str) -> str:
    """
    Economic Cycle Analysis: Economic cycle indicator dashboard collection (7 sources)

    Data collected:
    A. Money Supply, Interest Rates & Liquidity (4 indicators)
    B. Real Economy & Inflation (5 indicators)
    C. Risk, Credit & Debt (6 indicators including ECOS)
    D. Market Indices & Asset Prices (4 indicators)
    E. Valuation Indicators (3 scraped indicators)
    F. Market Sentiment (Fear & Greed Index)

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str: Economic cycle indicator summary (token-optimized, ~1,250 tokens)
    """
    # 1. Initialize
    is_korean_stock = ticker.isdigit()
    summary = f"--- ECONOMIC CYCLE DASHBOARD ({ticker}) ---\n"
    summary += f"Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    failed_sources = []
    total_indicators = 0
    successful_indicators = 0

    # 2. Load config
    from .macro_config import ECONOMIC_CYCLE_CONFIG

    # 3. GROUP A: Liquidity & Rates (FRED)
    summary += "=== A. Money Supply, Interest Rates & Liquidity ===\n"
    try:
        group_a = ECONOMIC_CYCLE_CONFIG['group_a_liquidity_rates']
        for ind in group_a['indicators']:
            total_indicators += 1
            fred_data = fetch_fred_data(ind['series_id'], ind['name'])

            if fred_data:
                successful_indicators += 1
                val_str = format_fred_value(fred_data['value'], ind['name'])
                prev_str = format_fred_value(fred_data['prev_value'], ind['name'])

                summary += f"- {ind['name']} ({ind['series_id']}): "
                summary += f"{val_str} ({fred_data['date']}) | "
                summary += f"Prev: {prev_str} | Δ: {fred_data['change_pct']:+.2f}%\n"
            else:
                failed_sources.append(f"{ind['name']}")

        # ECOS indicators for Group A (Korean liquidity/rates)
        if 'ecos_indicators' in group_a:
            for indicator_key, config in group_a['ecos_indicators'].items():
                total_indicators += 1
                ecos_data = fetch_ecos_data(
                    config['stat_code'],
                    config['item_code'],
                    config['cycle'],
                    config['name']
                )

                if ecos_data:
                    successful_indicators += 1
                    val_str = format_ecos_value(ecos_data['value'], config['name'])
                    prev_str = format_ecos_value(ecos_data['prev_value'], config['name'])

                    summary += f"- {config['name']}: "
                    summary += f"{val_str} ({ecos_data['date']}) | "
                    summary += f"Prev: {prev_str} | Δ: {ecos_data['change_pct']:+.2f}%\n"
                else:
                    failed_sources.append(f"{config['name']} (ECOS)")

        summary += "\n"
        time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Group A failed: {str(e)[:100]}\n\n"

    # 4. GROUP B: Real Economy (FRED)
    summary += "=== B. Real Economy & Inflation ===\n"
    try:
        group_b = ECONOMIC_CYCLE_CONFIG['group_b_real_economy']
        for ind in group_b['indicators']:
            total_indicators += 1
            fred_data = fetch_fred_data(ind['series_id'], ind['name'])

            if fred_data:
                successful_indicators += 1
                val_str = format_fred_value(fred_data['value'], ind['name'])
                prev_str = format_fred_value(fred_data['prev_value'], ind['name'])

                summary += f"- {ind['name']} ({ind['series_id']}): "
                summary += f"{val_str} ({fred_data['date']}) | "
                summary += f"Prev: {prev_str} | Δ: {fred_data['change_pct']:+.2f}%\n"
            else:
                failed_sources.append(f"{ind['name']}")

        # NEW: ECOS indicators for Group B (Korean economic indicators)
        if 'ecos_indicators' in group_b:
            for indicator_key, config in group_b['ecos_indicators'].items():
                total_indicators += 1

                # Multi-item indicator (BSI, Unemployment)
                if config.get('multi_item', False):
                    ecos_data = fetch_ecos_data_multi_item(
                        config['stat_code'],
                        config['item_codes'],
                        config['cycle'],
                        config['name'],
                        config.get('data_points')
                    )

                    if ecos_data:
                        for item_name, item_data in ecos_data.items():
                            successful_indicators += 1
                            summary += format_timeseries_output(item_data, item_name)
                    else:
                        failed_sources.append(f"{config['name']} (ECOS)")

                    time.sleep(0.2)  # Rate limiting for multi-item

                # Single-item indicator (GDP, CPI, PPI, CSI)
                else:
                    ecos_data = fetch_ecos_data_timeseries(
                        config['stat_code'],
                        config['item_code'],
                        config['cycle'],
                        config['name'],
                        config.get('data_points')
                    )

                    if ecos_data:
                        successful_indicators += 1
                        summary += format_timeseries_output(ecos_data, config['name'])
                    else:
                        failed_sources.append(f"{config['name']} (ECOS)")

        summary += "\n"
        time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Group B failed: {str(e)[:100]}\n\n"

    # 5. GROUP C: Risk & Credit (FRED + yfinance + ECOS)
    summary += "=== C. Risk, Credit & Debt ===\n"
    try:
        group_c = ECONOMIC_CYCLE_CONFIG['group_c_risk_credit']

        # FRED and yfinance indicators
        for ind in group_c['indicators']:
            total_indicators += 1

            if ind['source'] == 'FRED':
                fred_data = fetch_fred_data(ind['series_id'], ind['name'])
                if fred_data:
                    successful_indicators += 1
                    val_str = format_fred_value(fred_data['value'], ind['name'])
                    prev_str = format_fred_value(fred_data['prev_value'], ind['name'])

                    summary += f"- {ind['name']} ({ind['series_id']}): "
                    summary += f"{val_str} ({fred_data['date']}) | "
                    summary += f"Prev: {prev_str} | Δ: {fred_data['change_pct']:+.2f}%\n"
                else:
                    failed_sources.append(f"{ind['name']}")

            elif ind['source'] == 'yfinance':
                market_data = fetch_market_index(ind['series_id'], ind['name'])
                if market_data:
                    successful_indicators += 1
                    summary += f"- {ind['name']} ({ind['series_id']}): "
                    summary += f"{market_data['close']:,.2f} "
                    summary += f"({market_data['change_pct']:+.2f}%) "
                    summary += f"[{market_data['date']}]\n"
                else:
                    failed_sources.append(f"{ind['name']}")

        # ECOS indicators (Korean debt data)
        if 'ecos_indicators' in group_c:
            ecos_config = group_c['ecos_indicators']

            for debt_type, config in ecos_config.items():
                total_indicators += 1

                # Check if aggregation is required (e.g., Corporate Debt)
                if config.get('aggregation_required', False):
                    ecos_data = fetch_ecos_data_aggregated(
                        config['stat_code'],
                        config['item_code'],      # Base item code (e.g., 'BDDF1')
                        config['item_codes'],     # Sub-item codes (e.g., ['A', 'B'])
                        config['cycle'],
                        config['name']
                    )
                else:
                    ecos_data = fetch_ecos_data(
                        config['stat_code'],
                        config['item_code'],
                        config['cycle'],
                        config['name']
                    )

                if ecos_data:
                    successful_indicators += 1
                    val_str = format_ecos_value(ecos_data['value'], config['name'])
                    prev_str = format_ecos_value(ecos_data['prev_value'], config['name'])

                    summary += f"- {config['name']}: "
                    summary += f"{val_str} ({ecos_data['date']}) | "
                    summary += f"Prev: {prev_str} | Δ: {ecos_data['change_pct']:+.2f}%\n"
                else:
                    failed_sources.append(f"{config['name']} (ECOS)")

        summary += "\n"
        time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Group C failed: {str(e)[:100]}\n\n"

    # 6. GROUP D: Market Assets (yfinance)
    summary += "=== D. Market Indices & Asset Prices ===\n"
    try:
        group_d = ECONOMIC_CYCLE_CONFIG['group_d_market_assets']

        for ind in group_d['indicators']:
            total_indicators += 1

            if ind.get('type') == 'composite_ratio':
                # Commodity ratio (Copper/Gold)
                ratio_data = fetch_commodity_ratio(
                    ind['numerator'],
                    ind['denominator'],
                    ind['name']
                )

                if ratio_data:
                    successful_indicators += 1
                    summary += f"- {ind['name']}: {ratio_data['ratio']:.4f} "
                    summary += f"({ratio_data['date']}) | Δ: {ratio_data['change_pct']:+.2f}%\n"
                else:
                    failed_sources.append(f"{ind['name']}")

            else:
                # Regular market index
                market_data = fetch_market_index(ind['symbol'], ind['name'])

                if market_data:
                    successful_indicators += 1
                    summary += f"- {ind['name']} ({ind['symbol']}): "
                    summary += f"{market_data['close']:,.2f} "
                    summary += f"({market_data['change_pct']:+.2f}%) "
                    summary += f"[{market_data['date']}]\n"
                else:
                    failed_sources.append(f"{ind['name']}")

        summary += "\n"
        time.sleep(0.5)

    except Exception as e:
        summary += f"[!] Group D failed: {str(e)[:100]}\n\n"

    # 7. GROUP E: Valuation Metrics (AsyncChromiumLoader)
    summary += "=== E. Valuation Indicators ===\n"
    try:
        # ISM PMI
        total_indicators += 1
        ism_data = scrape_ism_pmi()
        if ism_data:
            successful_indicators += 1
            summary += f"- ISM Manufacturing PMI: {ism_data['actual']} "
            summary += f"| Forecast: {ism_data['forecast']} "
            summary += f"| Previous: {ism_data['previous']} [{ism_data['date']}]\n"
        else:
            failed_sources.append("ISM PMI")

        time.sleep(0.5)

        # Shiller PE
        total_indicators += 1
        shiller_data = async_scrape_shiller_pe()
        if shiller_data:
            successful_indicators += 1
            summary += f"- Shiller PE: {shiller_data['value']:.2f} "
            summary += f"| Change: {shiller_data['change']} [{shiller_data['date']}]\n"
        else:
            failed_sources.append("Shiller PE")

        time.sleep(0.5)

        # S&P 500 PE
        total_indicators += 1
        sp500_pe_data = async_scrape_sp500_pe()
        if sp500_pe_data:
            successful_indicators += 1
            summary += f"- S&P 500 PE-Ratio: {sp500_pe_data['value']:.2f} "
            summary += f"| Change: {sp500_pe_data['change'].replace('\n', ' ')} [{sp500_pe_data['date']}]\n"
        else:
            failed_sources.append("S&P 500 PE-Ratio")

        summary += "\n"

    except Exception as e:
        summary += f"[!] Group E failed: {str(e)[:100]}\n\n"

    # 8. Fear & Greed Index
    summary += "=== F. Market Sentiment ===\n"
    try:
        total_indicators += 1
        fgi_data = fetch_fear_greed_index()

        if fgi_data:
            successful_indicators += 1
            summary += f"- Fear & Greed Index: {fgi_data['value']}/100 - {fgi_data['description']}\n"
            summary += f"  Last Updated: {fgi_data['last_update']}\n"
        else:
            failed_sources.append("Fear & Greed Index")

        summary += "\n"

    except Exception as e:
        summary += f"[!] Fear & Greed failed: {str(e)[:100]}\n\n"

    # 9. Summary
    summary += "=== SUMMARY ===\n"

    # Count unique data sources
    sources_count = 7
    failed_source_types = set()
    if any('ECOS' in f for f in failed_sources):
        failed_source_types.add('ECOS')
    if any('ISM' in f for f in failed_sources):
        failed_source_types.add('ISM PMI')
    if any('Shiller' in f for f in failed_sources):
        failed_source_types.add('Shiller PE')
    if any('PE-Ratio' in f for f in failed_sources):
        failed_source_types.add('PE-Ratio')
    if any('Fear' in f for f in failed_sources):
        failed_source_types.add('Fear & Greed')

    successful_sources = sources_count - len(failed_source_types)
    summary += f"Data Sources: {successful_sources}/{sources_count}"
    if successful_sources == sources_count:
        summary += " ✓"
    summary += "\n"

    if total_indicators > 0:
        success_rate = (successful_indicators / total_indicators) * 100
        summary += f"Indicators: {successful_indicators}/{total_indicators} ({success_rate:.1f}%)\n"

    if failed_sources:
        unique_failures = list(set(failed_sources))[:10]  # Show max 10
        summary += f"Failed: {', '.join(unique_failures)}"
        if len(failed_sources) > 10:
            summary += f" +{len(failed_sources) - 10} more"
        summary += "\n"

    return summary


@tool
def get_fomc(ticker: str) -> str:
    """
    FOMC Document Collection: Retrieves latest FOMC Minutes and Statement.

    Collects official Federal Reserve monetary policy decision documents for use in Part 13 (Monetary Policy & Interest Rate Environment) analysis.

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str: Full text of FOMC Minutes and Statement (including title, date, content)
    """
    # Initialize
    summary = f"--- FOMC DOCUMENTS ({ticker}) ---\n"
    summary += f"Data Collection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    docs_collected = 0

    try:
        # Fetch FOMC documents
        data = get_latest_fomc_documents()

        if not data:
            summary += "[!] Failed to fetch FOMC documents from Federal Reserve website.\n"
            summary += "Please check network connection or try again later.\n"
            return summary

        # Section 1: FOMC Statement
        if 'statement' in data and data['statement']:
            stmt = data['statement']
            summary += "=== 1. FOMC STATEMENT ===\n"
            summary += f"Date: {stmt['date']}\n"
            summary += f"Title: {stmt['title']}\n"
            summary += f"URL: {stmt['url']}\n\n"

            if stmt['content']:
                summary += f"{stmt['content']}\n\n"
                docs_collected += 1
            else:
                summary += "[!] Content unavailable\n\n"
        else:
            summary += "=== 1. FOMC STATEMENT ===\n"
            summary += "[!] Statement not found\n\n"

        # Section 2: FOMC Minutes
        if 'minutes' in data and data['minutes']:
            mins = data['minutes']
            summary += "=== 2. FOMC MINUTES ===\n"
            summary += f"Date: {mins['date']}\n"
            summary += f"Title: {mins['title']}\n"
            summary += f"URL: {mins['url']}\n\n"

            if mins['content']:
                summary += f"{mins['content']}\n\n"
                docs_collected += 1
            else:
                summary += "[!] Content unavailable\n\n"
        else:
            summary += "=== 2. FOMC MINUTES ===\n"
            summary += "[!] Minutes not found\n\n"

    except Exception as e:
        summary += f"[!] Error during FOMC document collection: {str(e)[:150]}\n\n"

    # Summary
    summary += "=== SUMMARY ===\n"
    summary += f"Documents Collected: {docs_collected}/2"
    if docs_collected == 2:
        summary += " ✓"
    summary += "\n"
    summary += "Note: Full text of FOMC documents for comprehensive monetary policy analysis.\n"

    return summary
