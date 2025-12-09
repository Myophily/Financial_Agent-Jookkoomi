# tools/search.py
# Web search and news gathering tools

import os
import time
import asyncio
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse
from langchain.tools import tool
from langchain_community.document_loaders import WebBaseLoader
from tavily import TavilyClient
from GoogleNews import GoogleNews
from newspaper import Article
from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage

# --- Helper Functions ---

def calculate_month_ranges():
    """
    Divides the last 3 months into 3 monthly date ranges.
    Returns:
        list: List of tuples in the format [(start_date, end_date, label), ...]
    """
    today = datetime.now()

    # Month 1: Today to 30 days ago
    month1_end = today
    month1_start = today - timedelta(days=30)

    # Month 2: 30 days ago to 60 days ago
    month2_end = month1_start
    month2_start = today - timedelta(days=60)

    # Month 3: 60 days ago to 90 days ago
    month3_end = month2_start
    month3_start = today - timedelta(days=90)

    return [
        (month1_start, month1_end, f"Month 1 ({month1_start.strftime('%Y-%m-%d')} to {month1_end.strftime('%Y-%m-%d')})"),
        (month2_start, month2_end, f"Month 2 ({month2_start.strftime('%Y-%m-%d')} to {month2_end.strftime('%Y-%m-%d')})"),
        (month3_start, month3_end, f"Month 3 ({month3_start.strftime('%Y-%m-%d')} to {month3_end.strftime('%Y-%m-%d')})")
    ]

def extract_domain(url):
    """
    Extracts the domain from a URL (e.g., 'https://www.reuters.com/...' -> 'reuters.com').
    Args:
        url (str): URL string
    Returns:
        str: Domain name
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    except:
        return "unknown"

def should_skip_playwright_retry(error_msg):
    """
    Determines if AsyncChromium retry should be skipped based on error type.

    Args:
        error_msg (str): Error message or None
    Returns:
        bool: True if should skip retry, False otherwise
    """
    if not error_msg:
        return False

    # Skip retry for known hopeless cases
    skip_patterns = [
        '404', 'not found',
        '403', 'forbidden',
        '401', 'unauthorized',
        'paywall', 'subscription required',
        'captcha', 'blocked',
        'too many requests', '429'
    ]

    error_lower = str(error_msg).lower()
    return any(pattern in error_lower for pattern in skip_patterns)

def scrape_with_webbaseloader(url):
    """
    Extracts URL content using LangChain WebBaseLoader (fallback when newspaper3k fails).
    Retries with AsyncChromium if initial attempt fails.

    Args:
        url (str): Article URL
    Returns:
        dict: Article data or None (if failed)
    """
    # First attempt: Standard WebBaseLoader (fast)
    try:
        loader = WebBaseLoader(
            web_paths=[url],
            header_template={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            }
        )

        docs = loader.load()

        if docs and len(docs) > 0:
            content = docs[0].page_content
            # Check if we got meaningful content
            if content and len(content.strip()) > 100:
                return {
                    'title': docs[0].metadata.get('title', 'No Title'),
                    'date': 'Unknown',
                    'text': content,
                    'source': extract_domain(url),
                    'url': url,
                    'error': None,
                    'method': 'webbaseloader'
                }
    except Exception as e:
        error_msg = str(e)

        # Smart fallback: Skip AsyncChromium for known failures
        if should_skip_playwright_retry(error_msg):
            print(f"    ✗ [WebBaseLoader] Skipping AsyncChromium (known failure: {error_msg[:50]})")
            return None

    # Second attempt: AsyncChromium (slow but handles JS)
    print(f"    ⚠️  [WebBaseLoader] failed, trying AsyncChromium...")
    result = scrape_with_playwright(url)

    if result:
        return result

    return None

def scrape_with_playwright(url, retry_count=0, max_retries=2):
    """
    Extracts dynamic content using AsyncChromium Loader (fallback when WebBaseLoader fails).

    Args:
        url (str): Article URL
        retry_count (int): Current retry count
        max_retries (int): Maximum retry attempts
    Returns:
        dict: Article data or None (if failed)
    """
    try:
        from langchain_community.document_loaders import AsyncChromiumLoader

        print(f"    [AsyncChromium] attempt {retry_count + 1}/{max_retries + 1}: {url[:60]}...")

        # Load page using AsyncChromiumLoader with event loop wrapper
        loader = AsyncChromiumLoader(urls=[url])
        loader.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        docs = loop.run_until_complete(loader.aload())
        loop.close()

        if docs and len(docs) > 0:
            html_content = docs[0].page_content

            # Remove unwanted elements with BeautifulSoup
            selectors_to_remove = ["header", "footer", "nav", ".advertisement", ".ads", ".sidebar"]
            soup = BeautifulSoup(html_content, 'html.parser')
            for selector in selectors_to_remove:
                for element in soup.select(selector):
                    element.decompose()

            # Get cleaned content
            content = soup.get_text(strip=False)

            # Check for meaningful content
            if content and len(content.strip()) > 100:
                print(f"    ✓ [AsyncChromium] success (retry #{retry_count})")
                return {
                    'title': docs[0].metadata.get('title', 'No Title'),
                    'date': 'Unknown',
                    'text': content.strip(), # Clean whitespace when returning results
                    'source': extract_domain(url),
                    'url': url,
                    'error': None,
                    'method': 'asyncchromium'
                }
            else:
                print(f"    ⚠️  [AsyncChromium] insufficient content ({len(content.strip()) if content else 0} chars)")

    except ImportError:
        print("    ✗ [AsyncChromium] Not installed: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"    ⚠️  [AsyncChromium] error: {error_msg}")

        # Check if we should retry
        if retry_count < max_retries:
            # Check for timeout/network errors (retry-able)
            retryable_errors = ['timeout', 'network', 'connection', 'timed out']
            is_retryable = any(err in error_msg.lower() for err in retryable_errors)

            if is_retryable:
                # Exponential backoff: 2s → 4s
                delay = 2.0 * (2 ** retry_count)
                print(f"    ⏳ [retrying after.*seconds...]")
                time.sleep(delay)
                return scrape_with_playwright(url, retry_count + 1, max_retries)

    print(f"    ✗ [AsyncChromium] failed")
    return None


def scrape_article(url, timeout=15):
    """
    Scrapes articles using a 3-layer fallback strategy:
    1) Enhanced newspaper3k (custom headers)
    2) Standard newspaper3k (default settings)
    3) WebBaseLoader (LangChain)

    Args:
        url (str): Article URL
        timeout (int): Download timeout (seconds)
    Returns:
        dict: Article data (title, date, text, source, url, error, method)
    """

    # Attempt 1: Enhanced newspaper3k with custom headers
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=timeout)
        article = Article(url, language='en')
        article.set_html(response.text)
        article.parse()

        # Check if we got meaningful content
        if article.text and len(article.text.strip()) > 100:
            pub_date = None
            if article.publish_date:
                pub_date = article.publish_date.strftime('%Y-%m-%d')

            return {
                'title': article.title or 'No Title',
                'date': pub_date or 'Unknown',
                'text': article.text,
                'source': extract_domain(url),
                'url': url,
                'error': None,
                'method': 'newspaper3k'
            }
    except Exception:
        pass  # Continue to fallback

    # Attempt 2: Standard newspaper3k (original method)
    try:
        article = Article(url, language='en')
        article.download()
        article.parse()

        if article.text and len(article.text.strip()) > 100:
            pub_date = None
            if article.publish_date:
                pub_date = article.publish_date.strftime('%Y-%m-%d')

            return {
                'title': article.title or 'No Title',
                'date': pub_date or 'Unknown',
                'text': article.text,
                'source': extract_domain(url),
                'url': url,
                'error': None,
                'method': 'newspaper3k_fallback'
            }
    except Exception:
        pass  # Continue to WebBaseLoader fallback

    # Attempt 3: WebBaseLoader fallback
    webloader_result = scrape_with_webbaseloader(url)
    if webloader_result:
        return webloader_result

    # All methods failed
    return {
        'title': 'Scraping Failed',
        'date': 'Unknown',
        'text': '',
        'source': extract_domain(url),
        'url': url,
        'error': 'All scraping methods failed',
        'method': 'failed'
    }
# --- Tools ---

@tool
def tavily_search(query: str) -> str:
    """
    Searches for the latest information on the web using the Tavily search engine.
    (news, industry trends, executive information, etc.)
    Args:
        query (str): Search query string.
    Returns:
        str: Search results summary.
    """
    # try...except: Safety mechanism to prevent program crashes on errors
    try:
        # Create Tavily client using API key from .env
        tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        # Execute advanced search using the client
        results = tavily_client.search(query=query, search_depth="advanced", max_results=5)
        # Combine search results into a single string for AI
        return "\n".join([f"URL: {res['url']}\nContent: {res['content']}" for res in results['results']])
    except Exception as e:
        # Report error to AI if something goes wrong
        return f"Error during Tavily search: {e}"

def _process_summary_with_llm(raw_summary: str) -> str:
    """
    Processes the news summary with gemini-2.5-pro for better organization.
    Falls back to raw summary if processing fails.

    Args:
        raw_summary: The unprocessed summary markdown

    Returns:
        LLM-processed summary, or original if processing fails
    """
    # Lazy import to avoid circular dependency (llm.py imports from tools)
    from llm import model_flash_str

    # Check if model_flash_str is available
    if model_flash_str is None:
        print("⚠️  Warning: model_flash_str is None - skipping LLM processing for google_news_search")
        return raw_summary

    try:
        prompt = f"""The following is a Google News search result. Please improve the format and readability while preserving the content exactly as-is.

Requirements:
1. Preserve all data, statistics, and article titles (do not delete or summarize)
2. Organize markdown format consistently (heading levels, lists, tables, etc.)
3. Improve spacing and structure between sections. Remove empty lines.
4. Keep Korean text in Korean and English text in English
5. Remove article links.
6. Organize date formats consistently
7. Do not output articles that encountered errors.

Original report:

{raw_summary}

Please organize the above report according to requirements and output the improved version."""

        # Invoke LLM - Use string-returning chain for direct string output
        processed_summary = model_flash_str.invoke([HumanMessage(content=prompt)]).strip()

        # Validate output is not empty
        if not processed_summary:
            print("⚠️  Warning: LLM returned empty response for google_news_search - using original")
            return raw_summary

        print("✓ Successfully processed google_news_search summary with LLM")
        return processed_summary

    except Exception as e:
        print(f"⚠️  Error processing summary with LLM: {str(e)} - using original")
        return raw_summary

@tool
def google_news_search(company_name: str) -> str:
    """
    Collects news articles about a specific company from the last 3 months from Google News.
    Prioritizes high-credibility sources like Reuters and CNBC, scraping up to 30 articles per month (90 total).

    Args:
        company_name (str): Company name to search (e.g., "Samsung Electronics", "Tesla Inc").

    Returns:
        str: Structured text summary including article titles, sources, dates, and content.
    """
    try:
        # Initialize for tracking
        seen_urls = set()
        failed_articles = []
        articles_by_month = {}
        source_counts = {}

        # Calculate date ranges
        month_ranges = calculate_month_ranges()

        # Rate limiting configuration
        SCRAPE_DELAY = 0.5  # seconds

        # Search each month
        for start_date, end_date, month_label in month_ranges:
            monthly_articles = []

            try:
                # Initialize GoogleNews
                gn = GoogleNews(lang='en', region='US')
                gn.set_time_range(
                    start_date.strftime('%m/%d/%Y'),
                    end_date.strftime('%m/%d/%Y')
                )

                # Search
                gn.search(company_name)
                results = gn.results()

                # Filter by source priority
                tier1_sources = ['reuters.com', 'cnbc.com']
                tier2_sources = ['bloomberg.com', 'wsj.com', 'ft.com', 'marketwatch.com']

                tier1 = [r for r in results if extract_domain(r.get('link', '')) in tier1_sources]
                tier2 = [r for r in results if extract_domain(r.get('link', '')) in tier2_sources]
                all_others = [r for r in results if r not in tier1 and r not in tier2]

                # Select max 30 articles (Tier 1 priority)
                selected = tier1[:30]
                if len(selected) < 30:
                    selected.extend(tier2[:30 - len(selected)])
                if len(selected) < 30:
                    selected.extend(all_others[:30 - len(selected)])

                # Scrape each article
                for article_meta in selected[:30]:
                    url = article_meta.get('link', '')

                    # Skip duplicates
                    if url in seen_urls or not url:
                        continue

                    seen_urls.add(url)

                    # Scrape article
                    article_data = scrape_article(url)

                    # Track errors
                    if article_data.get('error'):
                        failed_articles.append({
                            'url': url,
                            'error': article_data['error'],
                            'month': month_label
                        })

                    monthly_articles.append(article_data)

                    # Track source counts
                    source = article_data['source']
                    source_counts[source] = source_counts.get(source, 0) + 1

                    # Rate limiting
                    time.sleep(SCRAPE_DELAY)

                articles_by_month[month_label] = monthly_articles

            except Exception as e:
                # Log and continue on monthly search failure
                articles_by_month[month_label] = []
                failed_articles.append({
                    'url': 'N/A',
                    'error': f"Month search failed: {str(e)}",
                    'month': month_label
                })

        # Format output string
        total_count = sum(len(articles) for articles in articles_by_month.values())

        summary = "=== GOOGLE NEWS ANALYSIS RESULTS ===\n"
        summary += f"Total articles collected: {total_count}\n"
        summary += f"Company searched: {company_name}\n"
        summary += f"Period: {month_ranges[-1][0].strftime('%Y-%m-%d')} ~ {month_ranges[0][1].strftime('%Y-%m-%d')}\n\n"

        summary += "[Statistics by Source]\n"
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            summary += f"- {source}: {count}\n"
        summary += "\n"

        # Add statistics by scraping method
        method_counts = {}
        for articles in articles_by_month.values():
            for article in articles:
                method = article.get('method', 'unknown')
                method_counts[method] = method_counts.get(method, 0) + 1

        summary += "[Scraping Method Statistics]\n"
        summary += f"- newspaper3k Success: {method_counts.get('newspaper3k', 0)}\n"
        summary += f"- newspaper3k (Fallback): {method_counts.get('newspaper3k_fallback', 0)}\n"
        summary += f"- WebBaseLoader (Fallback): {method_counts.get('webbaseloader', 0)}\n"
        summary += f"- AsyncChromium (Dynamic Content): {method_counts.get('asyncchromium', 0)}\n"
        summary += f"- Failed: {method_counts.get('failed', 0)}\n\n"

        summary += "━" * 50 + "\n\n"

        # Add monthly articles
        for month_label, articles in articles_by_month.items():
            summary += f"## Monthly News ({month_label})\n\n"

            if not articles:
                summary += "(No articles collected during this period)\n\n"
                continue

            for i, article in enumerate(articles, 1):
                summary += f"### [{i}] {article['title']}\n"
                summary += f"- **Source**: {article['source']}\n"
                summary += f"- **Date**: {article['date']}\n"
                summary += f"- **URL**: {article['url']}\n"
                summary += f"- **Content**:\n{article['text']}\n\n"

            summary += "━" * 50 + "\n\n"

        # Add error logs
        if failed_articles:
            summary += "[Error Report]\n"
            summary += f"- Failed Articles: {len(failed_articles)}\n"
            for i, failure in enumerate(failed_articles[:10], 1):  # Limit to 10
                summary += f"  {i}. {failure['url']}: {failure['error'][:100]}\n"
            if len(failed_articles) > 10:
                summary += f"  ... and {len(failed_articles) - 10} more\n"

        # Process with LLM for better organization
        final_summary = _process_summary_with_llm(summary)
        return final_summary

    except Exception as e:
        return f"Error during Google News search: {e}"
