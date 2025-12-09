# tools/financial.py
# Financial data fetching and analysis tools

import os
from datetime import datetime, timedelta
from langchain.tools import tool
import yfinance as yf
from pykrx.stock import get_market_fundamental
from pykrx import stock as pykrx_stock


@tool
def get_financial_data(ticker: str) -> str:
    """
    Fetches key financial data using domestic or foreign stock tickers.
    (pykrx: domestic stock fundamentals / yfinance: financial statements)
    Args:
        ticker (str): Stock ticker to analyze (e.g., '005930' or 'AAPL').
    Returns:
        str: Summary string of key financial statements and ratios.
    """
    try:
        is_korean_stock = ticker.isdigit()
        summary_data = {} # Dictionary to store summary information

        # 1. If it's a Korean stock, get accurate valuation first using pykrx
        if is_korean_stock:
            try:
                # Get fundamental information for the most recent business day based on today's date.
                today_str = datetime.now().strftime("%Y%m%d")
                start_date_str = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                
                # Retrieve BPS, PER, PBR, EPS, DIV, DPR etc. using pykrx
                df_krx = pykrx_stock.get_market_fundamental(start_date_str, today_str, ticker)
                
                if not df_krx.empty:
                    latest_krx = df_krx.iloc[-1] # Data from the latest date
                    summary_data['PER'] = f"{latest_krx.get('PER', 'N/A')}"
                    summary_data['PBR'] = f"{latest_krx.get('PBR', 'N/A')}"
                    summary_data['DIV'] = f"{latest_krx.get('DIV', 'N/A')}%" # Dividend yield
            except Exception as e:
                print(f"pykrx query failed: {e}")

        # 2. Fetch financial statements using yfinance
        yf_ticker = f"{ticker}.KS" if is_korean_stock else ticker
        stock = yf.Ticker(yf_ticker)
        
        info = stock.info
        
        # Use yfinance information if it's not a Korean stock or if pykrx failed
        if 'PER' not in summary_data:
            summary_data['PER'] = info.get('trailingPE', 'N/A')
        if 'PBR' not in summary_data:
            summary_data['PBR'] = info.get('priceToBook', 'N/A')
            
        # Fetch financial statements (clean NaN values and slice to the latest 3 years)
        # axis=1 means columns (year), how='all' deletes only if all values are NaN
        financials = stock.financials.dropna(axis=1, how='all').iloc[:, :3]
        balance_sheet = stock.balance_sheet.dropna(axis=1, how='all').iloc[:, :3]
        cashflow = stock.cashflow.dropna(axis=1, how='all').iloc[:, :3]

        # 3. Generate Report (Summary)
        summary = f"--- Financial Data Report ({ticker}) ---\n"
        summary += f"Company Name: {info.get('shortName', ticker)}\n"
        summary += f"Sector/Industry: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}\n"
        summary += f"Market Cap: {info.get('marketCap', 'N/A'):,}\n"
        summary += f"PER: {summary_data.get('PER')}\n"
        summary += f"PBR: {summary_data.get('PBR')}\n"
        if 'DIV' in summary_data:
             summary += f"Dividend Yield (KRX): {summary_data['DIV']}\n"

        summary += f"\n[1] Income Statement (Latest 3 Years)\n{financials.to_string()}\n"
        summary += f"\n[2] Balance Sheet (Latest 3 Years)\n{balance_sheet.to_string()}\n"
        summary += f"\n[3] Cash Flow Statement (Latest 3 Years)\n{cashflow.to_string()}\n"

        return summary

    except Exception as e:
        return f"Error fetching financial data ({ticker}): {str(e)}"

@tool
def get_historical_data(ticker: str) -> str:
    """
    Fetches 1-year historical price data for a stock.
    (Includes daily open, high, low, close, volume)
    Args:
        ticker (str): Stock ticker to analyze (e.g., '005930' or 'AAPL').
    Returns:
        str: Summary and detailed breakdown of 1-year historical price data.
    """
    try:
        # 1. Check if the ticker consists only of digits (to determine if it's a Korean stock).
        is_korean_stock = ticker.isdigit()

        # 2. Prepare the yfinance ticker.
        yf_ticker = ticker
        if is_korean_stock:
            yf_ticker = f"{ticker}.KS"

        # 3. Create a stock object using yfinance.
        stock = yf.Ticker(yf_ticker)

        # 4. Get 1 year (1y) historical data.
        hist = stock.history(period="1y")

        # 5. Check if the data is empty.
        if hist.empty:
            return f"Historical data not found ({ticker})"

        # 6. Assemble the summary information to report to the AI.
        summary = f"--- 1-Year Historical Price Data ({ticker}) ---\n"
        summary += f"Data Period: {hist.index[0].strftime('%Y-%m-%d')} ~ {hist.index[-1].strftime('%Y-%m-%d')}\n"
        summary += f"Current Price: {hist['Close'].iloc[-1]:.2f}\n"
        summary += f"52-Week High: {hist['High'].max():.2f}\n"
        summary += f"52-Week Low: {hist['Low'].min():.2f}\n"
        summary += f"Average Volume: {hist['Volume'].mean():.0f}\n"
        summary += f"Total Trading Days: {len(hist)}\n"

        # 7. Add detailed price data table.
        summary += f"\n--- Daily Price Data (Full Year) ---\n"
        # Display all 1-year data.
        summary += hist.to_string()

        # 8. Return the assembled string.
        return summary

    except Exception as e:
        # Report error to AI.
        return f"Error fetching historical data ({ticker}): {e}"
