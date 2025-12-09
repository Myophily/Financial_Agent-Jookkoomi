# tools/sentiment.py
# Market sentiment and social media analysis tools

import os
import time
from datetime import datetime
from langchain.tools import tool
import yfinance as yf
import praw
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pykrx')


# --- Tools ---

@tool
def get_market_sentiment(ticker: str) -> str:
    """
    Market sentiment analysis: Collects data from 4 sources.
    1) finvizfinance: News headlines and insider trading
    2) fear-and-greed: CNN Fear & Greed Index
    3) nasdaq-data-link: Institutional futures positioning (CFTC data)
    4) yfinance: Analyst recommendations and price targets

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str: Sentiment analysis report from 4 sources (formatted by sections)
    """
    import time

    # Detect Korean stock (numeric ticker = Korean stock)
    is_korean_stock = ticker.isdigit()
    yf_ticker = f"{ticker}.KS" if is_korean_stock else ticker

    summary = f"--- MARKET SENTIMENT ANALYSIS ({ticker}) ---\n\n"
    failed_sources = []

    # ===== SOURCE 1: finvizfinance (News + Insider Trading) =====
    summary += "=== 1. NEWS & INSIDER TRADING (finvizfinance) ===\n"

    if is_korean_stock:
        summary += "[!] finviz does not support Korean stocks (.KS).\n\n"
        failed_sources.append("finviz")
    else:
        try:
            from finvizfinance.quote import finvizfinance
            stock = finvizfinance(ticker)

            # News headlines (recent 10)
            news_data = stock.ticker_news()
            if not news_data.empty:
                summary += "[Recent News Headlines]\n"
                news_top = news_data.head(10)
                for idx, (_, row) in enumerate(news_top.iterrows(), 1):
                    title = row.get('Title', 'N/A')
                    date = row.get('Date', 'N/A')
                    link = row.get('Link', 'N/A')
                    source = row.get('Source', 'N/A')
                    summary += f"{idx}. {title} | {date} | {source}\n   {link}\n"
                summary += "\n"
            else:
                summary += "[!] News data not found.\n\n"

            # Insider trading (recent 20)
            insider_data = stock.ticker_inside_trader()
            if not insider_data.empty:
                summary += "[Insider Trading Activity]\n"
                insider_top = insider_data.head(20)
                for _, row in insider_top.iterrows():
                    trader = row.get('Insider Trading', 'N/A')
                    relationship = row.get('Relationship', 'N/A')
                    date = row.get('Date', 'N/A')
                    transaction = row.get('Transaction', 'N/A')
                    shares = row.get('#Shares', 'N/A')
                    value = row.get('Value ($)', 'N/A')
                    summary += f"- {date} | {trader} ({relationship}) | {transaction} | Shares: {shares:,.0f} | Value: ${value:,.0f}\n"
                summary += "\n"
            else:
                summary += "[!] Insider trading data not found.\n\n"

        except Exception as e:
            summary += f"[!] finviz data collection failed: {str(e)[:150]}\n\n"
            failed_sources.append("finviz")

    time.sleep(0.5)

    # ===== SOURCE 2: fear-and-greed (Fear & Greed Index) =====
    summary += "=== 2. FEAR & GREED INDEX (Market-Wide) ===\n"

    try:
        import fear_and_greed
        fgi = fear_and_greed.get()

        summary += f"Current Index: {fgi.value}/100 - {fgi.description}\n"
        summary += f"Last Updated: {fgi.last_update}\n"
        summary += "(Note: Market-wide index, not specific to individual stocks)\n\n"

    except Exception as e:
        summary += f"[!] Fear & Greed Index collection failed: {str(e)[:150]}\n\n"
        failed_sources.append("fear-greed")

    time.sleep(0.5)

    # ===== SOURCE 3: INSTITUTIONAL OWNERSHIP & MARKET POSITIONING (yfinance) =====
    summary += "=== 3. INSTITUTIONAL OWNERSHIP & MARKET POSITIONING ===\n"

    try:
        stock = yf.Ticker(yf_ticker)

        # 3.1: Major Holders Breakdown (FIXED)
        try:
            major_holders = stock.major_holders
            if major_holders is not None and not major_holders.empty:
                summary += "[Major Holders Breakdown]\n"
                
                # Case A: Single column (Index acts as Label) - error previously occurred here
                if major_holders.shape[1] == 1:
                    for idx, row in major_holders.iterrows():
                        # idx is label (e.g., "% of Shares Held..."), row.iloc[0] is value
                        val = row.iloc[0]
                        summary += f"  {idx}: {val}\n"
                
                # Case B: Two columns (column 0 and 1 are Label/Value respectively)
                elif major_holders.shape[1] >= 2:
                    for _, row in major_holders.iterrows():
                        val0 = row.iloc[0]
                        val1 = row.iloc[1]
                        
                        # Check which side is value (number/%) and format accordingly
                        str_v0 = str(val0)
                        if any(c.isdigit() for c in str_v0) or '%' in str_v0:
                             summary += f"  {val1}: {val0}\n"
                        else:
                             summary += f"  {val0}: {val1}\n"
                summary += "\n"
        except Exception as e:
            summary += f"[!] Major holders data unavailable: {str(e)}\n\n"

        # 3.2: Top Institutional Holders
        try:
            institutional_holders = stock.institutional_holders
            if institutional_holders is not None and not institutional_holders.empty:
                summary += "[Top 15 Institutional Holders]\n"
                summary += "%-40s %10s %15s %15s %10s\n" % ("Holder", "% Held", "Shares", "Value ($)", "% Change")
                summary += "-" * 93 + "\n"

                for _, row in institutional_holders.head(15).iterrows():
                    holder = str(row.get('Holder', 'N/A'))[:40]
                    pct = row.get('pctHeld', 0)
                    shares = row.get('Shares', 0)
                    value = row.get('Value', 0)
                    change = row.get('pctChange', 0)

                    try:
                        summary += f"{holder:<40} {pct:>9.2%} {int(shares):>15,} ${int(value):>14,} {change:>+9.2%}\n"
                    except:
                        summary += f"{holder:<40} {str(pct):>10} {str(shares):>15} {str(value):>15} {str(change):>10}\n"

                summary += "\n"
        except Exception:
            summary += "[!] Institutional holders data unavailable\n\n"

        # 3.3: Short Interest
        try:
            info = stock.info
            short_ratio = info.get('shortRatio')
            short_pct_float = info.get('shortPercentOfFloat')
            shares_short = info.get('sharesShort')

            if short_ratio or short_pct_float or shares_short:
                summary += "[Short Interest Metrics]\n"
                if short_ratio:
                    summary += f"  Short Ratio (Days to Cover): {short_ratio:.2f}\n"
                if short_pct_float:
                    summary += f"  Short % of Float: {short_pct_float:.2%}\n"
                if shares_short:
                    summary += f"  Shares Short: {int(shares_short):,}\n"

                if short_pct_float:
                    if short_pct_float > 0.20:
                        summary += "  → High short interest (bearish sentiment)\n"
                    elif short_pct_float > 0.10:
                        summary += "  → Moderate short interest\n"
                    else:
                        summary += "  → Low short interest (bullish sentiment)\n"

                summary += "\n"
            elif is_korean_stock:
                summary += "[Short Interest Metrics]\n"
                summary += "  (Short interest data is limited for Korean stocks)\n\n"
        except Exception:
            if not is_korean_stock:
                summary += "[!] Short interest data unavailable\n\n"

        # 3.4: Options Flow
        if not is_korean_stock:
            try:
                expirations = stock.options
                if expirations and len(expirations) > 0:
                    summary += "[Options Flow - Put/Call Ratio]\n"
                    total_calls_vol, total_puts_vol = 0, 0
                    total_calls_oi, total_puts_oi = 0, 0

                    for exp in expirations[:2]:
                        opt = stock.option_chain(exp)
                        total_calls_vol += opt.calls['volume'].fillna(0).sum()
                        total_puts_vol += opt.puts['volume'].fillna(0).sum()
                        total_calls_oi += opt.calls['openInterest'].fillna(0).sum()
                        total_puts_oi += opt.puts['openInterest'].fillna(0).sum()

                    pcr_volume = total_puts_vol / total_calls_vol if total_calls_vol > 0 else None
                    pcr_oi = total_puts_oi / total_calls_oi if total_calls_oi > 0 else None

                    if pcr_volume:
                        summary += f"  Put/Call Ratio (Volume): {pcr_volume:.3f}\n"
                    if pcr_oi:
                        summary += f"  Put/Call Ratio (Open Interest): {pcr_oi:.3f}\n"

                    if pcr_volume and pcr_oi:
                        avg_pcr = (pcr_volume + pcr_oi) / 2
                        if avg_pcr < 0.7:
                            summary += "  → Bullish sentiment (more calls than puts)\n"
                        elif avg_pcr > 1.3:
                            summary += "  → Bearish sentiment (more puts than calls)\n"
                        else:
                            summary += "  → Neutral sentiment\n"
                    summary += f"  (Based on nearest 2 expirations: {', '.join(expirations[:2])})\n\n"
            except Exception:
                summary += "[!] Options data unavailable for this ticker\n\n"
        else:
            summary += "[Options Flow]\n"
            summary += "  (Options data is not available for Korean stocks)\n\n"

    except Exception as e:
        summary += f"[!] Institutional positioning data collection failed: {str(e)[:150]}\n\n"
        failed_sources.append("institutional-data")

    time.sleep(0.5)

    # ===== SOURCE 4: yfinance (Analyst Recommendations) =====
    summary += "=== 4. ANALYST RECOMMENDATIONS (yfinance) ===\n"

    try:
        stock = yf.Ticker(yf_ticker)
        info = stock.info

        # Target price information
        target_mean = info.get('targetMeanPrice', 'N/A')
        target_high = info.get('targetHighPrice', 'N/A')
        target_low = info.get('targetLowPrice', 'N/A')
        current = info.get('currentPrice', 'N/A')

        summary += f"Target Price (Mean): ${target_mean}\n"
        summary += f"Target Price Range: ${target_low} - ${target_high}\n"
        summary += f"Current Price: ${current}\n"

        if target_mean != 'N/A' and current != 'N/A':
            try:
                upside = ((float(target_mean) - float(current)) / float(current)) * 100
                summary += f"Upside Potential: {upside:+.2f}%\n"
            except:
                pass

        summary += "\n"

        # Analyst recommendation distribution
        recommendations = stock.recommendations

        if recommendations is not None and not recommendations.empty:
            summary += "[Recommendations Breakdown - Recent]\n"
            recent = recommendations.tail(1) 
            
            # Support for yfinance latest version
            if 'strongBuy' in recent.columns and 'buy' in recent.columns:
                try:
                    latest = recent.iloc[-1]
                    period = latest.get('period', 'Latest')
                    sb = latest.get('strongBuy', 0)
                    b = latest.get('buy', 0)
                    h = latest.get('hold', 0)
                    s = latest.get('sell', 0)
                    ss = latest.get('strongSell', 0)
                    summary += f"Period: {period}\n"
                    summary += f"Strong Buy: {sb} | Buy: {b} | Hold: {h} | Sell: {s} | Strong Sell: {ss}\n"
                except Exception as e:
                     summary += f"Error parsing recommendations: {e}\n"

            # Support for older version
            elif 'To Grade' in recent.columns:
                grade_counts = recent['To Grade'].value_counts()
                strong_buy = grade_counts.get('Strong Buy', 0) + grade_counts.get('Outperform', 0)
                buy = grade_counts.get('Buy', 0)
                hold = grade_counts.get('Hold', 0) + grade_counts.get('Neutral', 0)
                sell = grade_counts.get('Sell', 0) + grade_counts.get('Underperform', 0)
                strong_sell = grade_counts.get('Strong Sell', 0)
                summary += f"Strong Buy/Outperform: {strong_buy} | Buy: {buy} | Hold/Neutral: {hold} | Sell: {sell} | Strong Sell: {strong_sell}\n"
            
            summary += "\n"
        else:
            summary += "[!] Analyst recommendation data not found.\n\n"

    except Exception as e:
        summary += f"[!] yfinance analyst data collection failed: {str(e)[:150]}\n\n"
        failed_sources.append("yfinance")

    # ===== SUMMARY =====
    summary += "=== SUMMARY ===\n"
    successful = 4 - len(failed_sources)
    summary += f"Data Sources Collected: {successful}/4\n"

    if failed_sources:
        summary += f"Failed Sources: {', '.join(failed_sources)}\n"

    return summary


def get_company_name_for_search(ticker: str) -> str:
    """
    Fetches company name from ticker using yfinance.
    Returns None if fetch fails (to gracefully fallback to ticker-only search).

    Args:
        ticker (str): Stock ticker (e.g., 'AAPL', '005930')

    Returns:
        str or None: Company name or None if unavailable
    """
    try:
        # Detect Korean stock (numeric ticker)
        is_korean_stock = ticker.isdigit()
        yf_ticker = f"{ticker}.KS" if is_korean_stock else ticker

        # Fetch company info using yfinance
        stock = yf.Ticker(yf_ticker)
        info = stock.info

        # Return shortName or longName
        company_name = info.get('shortName', info.get('longName', None))
        return company_name
    except Exception:
        # Silently fail and return None for graceful fallback
        return None


@tool
def scrap_reddit(ticker: str, subreddits: str = "stocks,wallstreetbets",
                 max_posts: int = 50, top_comments: int = 5) -> str:
    """
    Collects discussions and comments about a specific stock from Reddit.
    Automatically searches using BOTH ticker symbol AND company name for comprehensive coverage.
    (Last 1 month, includes Title + Body + Top Comments)

    Args:
        ticker (str): Stock ticker to search (e.g., 'AAPL', 'TSLA', '005930')
                      Company name is automatically fetched via yfinance
        subreddits (str): Subreddits to search (comma-separated, default: "stocks,wallstreetbets")
        max_posts (int): Maximum number of posts to collect (default: 50)
        top_comments (int): Number of top comments to collect per post (default: 5)

    Returns:
        str: Structured text summary including titles, bodies, and comments

    Note:
        - Searches Reddit using both ticker and company name
        - Deduplicates posts that appear in both searches
        - Gracefully falls back to ticker-only search if company name unavailable
    """
    try:
        # 1. Initialize Reddit client
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")

        if not reddit_client_id or not reddit_secret:
            return "[!] REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set in .env.\n" \
                   "    https://www.reddit.com/prefs/apps and set up credentials."

        reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_secret,
            user_agent="JooKkoomi Stock Analyzer v1.0"
        )

        # 2. Fetch company name for enhanced search
        company_name = get_company_name_for_search(ticker)
        search_queries = [ticker]
        if company_name:
            search_queries.append(company_name)

        # 3. Parse subreddits
        subreddit_list = [s.strip() for s in subreddits.split(',') if s.strip()]
        if not subreddit_list:
            return "No valid subreddit provided."

        # 4. Distribute post limit across subreddits
        posts_per_subreddit = max_posts // len(subreddit_list)
        remaining = max_posts % len(subreddit_list)

        # 5. Collect posts (with deduplication)
        collected_posts = []
        subreddit_counts = {}
        failed_subreddits = []
        comment_errors = 0
        seen_post_ids = set()  # Track post IDs to avoid duplicates

        for idx, subreddit_name in enumerate(subreddit_list):
            limit = posts_per_subreddit + (1 if idx < remaining else 0)

            try:
                subreddit = reddit.subreddit(subreddit_name)
                _ = subreddit.display_name  # Test access

                # Search for both ticker and company name mentions
                for query in search_queries:
                    for submission in subreddit.search(
                        query=query,
                        time_filter='month',
                        sort='relevance',
                        limit=limit
                    ):
                        # Skip if already seen (deduplication)
                        if submission.id in seen_post_ids:
                            continue
                        seen_post_ids.add(submission.id)

                        # Load comments
                        comments_data = []
                        try:
                            submission.comments.replace_more(limit=0)
                            sorted_comments = sorted(
                                submission.comments,
                                key=lambda c: c.score,
                                reverse=True
                            )[:top_comments]

                            comments_data = [
                                {
                                    'author': str(c.author) if c.author else '[deleted]',
                                    'score': c.score,
                                    'body': c.body
                                }
                                for c in sorted_comments
                            ]
                        except Exception:
                            comment_errors += 1

                        # Collect post data
                        collected_posts.append({
                            'subreddit': subreddit_name,
                            'title': submission.title,
                            'author': str(submission.author) if submission.author else '[deleted]',
                            'score': submission.score,
                            'num_comments': submission.num_comments,
                            'created_utc': submission.created_utc,
                            'selftext': submission.selftext,
                            'url': submission.url,
                            'comments': comments_data
                        })

                        subreddit_counts[subreddit_name] = subreddit_counts.get(subreddit_name, 0) + 1

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                failed_subreddits.append(f"{subreddit_name}: {str(e)[:50]}")

        # 5. Check if any results
        if not collected_posts:
            msg = f"Cannot find Reddit discussion for\n"
            msg += f"Period: Last 1 month\n"
            msg += f"Searched subreddits: {', '.join([f'r/{s}' for s in subreddit_list])}\n"
            if failed_subreddits:
                msg += f"\nAccess failed: {', '.join(failed_subreddits)}"
            return msg

        # 6. Format output
        summary = "=== REDDIT DISCUSSION ANALYSIS RESULTS ===\n"
        summary += f"Total Collected Posts: {len(collected_posts)}\n"
        summary += f"Search Ticker: {ticker}\n"
        if company_name:
            summary += f"Company Name: {company_name}\n"
            summary += f"Search Queries: {', '.join([f'{q!r}' for q in search_queries])}\n"
        else:
            summary += f"Search Query: '{ticker}' (Company name lookup failed, searching ticker only)\n"
        summary += f"Subreddits: {', '.join([f'r/{s}' for s in subreddit_list])}\n"
        summary += f"Timeframe: Last 1 month\n\n"

        summary += "[Statistics by Subreddit]\n"
        for sub, count in sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True):
            summary += f"- r/{sub}: {count}\n"
        summary += "\n"

        summary += "━" * 50 + "\n\n"

        # Group by subreddit
        by_subreddit = {}
        for post in collected_posts:
            sub = post['subreddit']
            if sub not in by_subreddit:
                by_subreddit[sub] = []
            by_subreddit[sub].append(post)

        # Output posts by subreddit
        for subreddit_name, posts in by_subreddit.items():
            summary += f"## r/{subreddit_name} Discussion\n\n"

            for i, post in enumerate(posts, 1):
                date_str = datetime.fromtimestamp(post['created_utc']).strftime('%Y-%m-%d')

                summary += f"### [{i}] {post['title']}\n"
                summary += f"- **Author**: u/{post['author']}\n"
                summary += f"- **Date**: {date_str}\n"
                summary += f"- **Score**: {post['score']} upvotes\n"
                summary += f"- **Comments**: {post['num_comments']}\n"
                summary += f"- **URL**: {post['url']}\n\n"

                if post['selftext']:
                    summary += f"**Body**:\n{post['selftext']}\n\n"
                else:
                    summary += "**Body**: (Link post)\n\n"

                if post['comments']:
                    summary += f"**Top Comments ({len(post['comments'])})**:\n\n"
                    for j, comment in enumerate(post['comments'], 1):
                        summary += f"[Comment {j}] ({comment['score']} upvotes) - u/{comment['author']}\n"
                        summary += f"{comment['body']}\n\n"
                else:
                    summary += "**Comments**: (No comments or loading failed)\n\n"

            summary += "━" * 50 + "\n\n"

        # Error report
        if failed_subreddits or comment_errors > 0:
            summary += "[Error Report]\n"
            if comment_errors > 0:
                summary += f"- Comment loading failed: {comment_errors} posts\n"
            if failed_subreddits:
                summary += f"- Inaccessible subreddits: {len(failed_subreddits)}\n"
                for failure in failed_subreddits[:5]:  # Show first 5
                    summary += f"  {failure}\n"

        return summary

    except Exception as e:
        return f"Error collecting Reddit data: {e}"
