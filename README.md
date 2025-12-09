# JooKkoomi

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13+-blue.svg" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/license-TBD-lightgrey.svg" alt="License">
  <img src="https://img.shields.io/badge/LangGraph-powered-green.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/AI-Google%20Gemini%202.5-4285F4.svg" alt="Google Gemini 2.5">
</p>

**AI-Powered Stock Analysis Agent | Comprehensive Investment Reports for US & Korean Markets**

---

## Overview

JooKkoomi is an autonomous AI agent that generates institutional-grade stock analysis reports by orchestrating 16 specialized analysis workflows. Powered by Google's Gemini 2.5 Pro with extended thinking capabilities, it analyzes both US and Korean stocks across fundamental, technical, sentiment, and macroeconomic dimensions.

**Why JooKkoomi?**

- **Comprehensive**: 16-part analysis covering everything from financial statements to macroeconomic policy impact
- **Autonomous**: Set it and forget it with cron-based daily execution
- **Bilingual**: Generates reports in both English and Korean
- **Transparent**: Built-in cost tracking and execution monitoring
- **Multi-source**: Integrates 14 data sources (yfinance, Reddit, FRED, Google Trends, ECOS, and more)

**Perfect for**: Individual investors seeking institutional-quality research, financial analysts automating routine analysis, or data scientists building investment workflows.

---

## Key Features

- 16-part sequential analysis workflow across 4 dimensions (Fundamental, Technical, Sentiment, Macro)
- AI-powered synthesis using Gemini 2.5 Pro with experimental thinking mode
- Dual-market support: US stocks (NASDAQ, NYSE) & Korean stocks (KRX)
- Automated PDF report generation with email delivery to multiple recipients
- Cron-compatible queue system for daily automated runs
- Built-in cost tracking and execution monitoring (JSON logs)
- Bilingual output: English + optional Korean translation
- 14 specialized analysis tools across 7 categories
- Resilient error handling with automatic retry logic
- Thread-safe queue management for concurrent execution prevention

---

## Quick Start

Get your first analysis running in 10 minutes:

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd jookkoomi-public
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure (minimum required)
cp .env.example .env
# Edit .env and add these required keys:
# - GOOGLE_API_KEY (Gemini 2.5 Pro)
# - GMAIL_USER and GMAIL_APP_PASSWORD
# - RECIPIENT_EMAILS

# 3. Run your first analysis
python main.py AAPL

# 4. Check your email for the PDF report!
```

---

## Installation

### Prerequisites

- **Python 3.10 or higher**
- **Gmail account with 2FA enabled** (for report delivery)
- **Google Cloud account** with Gemini API access

### Step-by-Step Installation

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd jookkoomi-public
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv

   # Activate (macOS/Linux)
   source venv/bin/activate

   # Activate (Windows)
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env file with your API keys (see Configuration section)
   ```

5. **Verify installation**
   ```bash
   python main.py
   # Should display usage instructions
   ```

---

## Configuration

### API Keys & Environment Setup

JooKkoomi requires multiple API keys for comprehensive analysis. Below is a tiered breakdown:

#### Tier 1: Required Keys (System Won't Run Without These)

| Service                 | Key Name               | Purpose                              | Get It Here                                                      | Setup Time |
| ----------------------- | ---------------------- | ------------------------------------ | ---------------------------------------------------------------- | ---------- |
| **Google Gemini**       | `GOOGLE_API_KEY`       | Main AI brain (gemini-2.5-pro)       | [Google AI Studio](https://makersuite.google.com/app/apikey)     | 2 min      |
| **Google Gemini Flash** | `GOOGLE_API_KEY_FLASH` | Report formatting (gemini-2.5-flash) | [Google AI Studio](https://makersuite.google.com/app/apikey)     | 2 min      |
| **Gmail**               | `GMAIL_USER`           | Email sender address                 | Your Gmail account                                               | 1 min      |
| **Gmail**               | `GMAIL_APP_PASSWORD`   | Email authentication                 | [Gmail App Passwords](https://myaccount.google.com/apppasswords) | 5 min      |
| **Recipients**          | `RECIPIENT_EMAILS`     | Report recipients                    | Your choice                                                      | 1 min      |

**Gmail App Password Setup**:

1. Enable 2-factor authentication on your Google account: [Security Settings](https://myaccount.google.com/security)
2. Generate app password: [App Passwords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Other" (custom name: "JooKkoomi")
4. Copy the 16-character password to `.env` file

**Recipient Emails Format**:

```env
RECIPIENT_EMAILS="investor1@example.com,analyst2@example.com,team@company.com"
```

#### Tier 2: Highly Recommended Keys (Quality Degradation Without)

| Service    | Key Name               | Purpose                         | Get It Here                                             | Free Tier   |
| ---------- | ---------------------- | ------------------------------- | ------------------------------------------------------- | ----------- |
| **Reddit** | `REDDIT_CLIENT_ID`     | Social sentiment (Part 11)      | [Reddit Apps](https://www.reddit.com/prefs/apps)        | Yes         |
| **Reddit** | `REDDIT_CLIENT_SECRET` | Social sentiment (Part 11)      | [Reddit Apps](https://www.reddit.com/prefs/apps)        | Yes         |
| **ECOS**   | `ECOS_API_KEY`         | Korean macro data (Parts 12-14) | [BOK ECOS](https://ecos.bok.or.kr/api/)                 | Yes         |
| **FMP**    | `FMP_API_KEY`          | Enhanced financial data         | [FMP](https://financialmodelingprep.com/developer/docs) | 250 req/day |

**Reddit App Setup**:

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Select "script" type
4. Fill in name (e.g., "JooKkoomi") and redirect URI (use `http://localhost:8080`)
5. Copy client ID (under app name) and secret to `.env`

#### Tier 3: Optional Keys (Specific Feature Enhancement)

| Service    | Key Name         | Purpose                | Get It Here                  | Cost   |
| ---------- | ---------------- | ---------------------- | ---------------------------- | ------ |
| **Tavily** | `TAVILY_API_KEY` | Web search enhancement | [Tavily](https://tavily.com) | $50/mo |

#### Other Configuration

| Key Name               | Purpose                                        | Default Value  |
| ---------------------- | ---------------------------------------------- | -------------- |
| `MONITOR_FULL_CONTENT` | Log full content (true) or counts only (false) | `true`         |
| `USER_AGENT`           | HTTP user agent string                         | Mozilla/5.0... |

### Example .env File

```env
# Required
GOOGLE_API_KEY="AIza..."
GOOGLE_API_KEY_FLASH="AIza..."
GMAIL_USER="your@gmail.com"
GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
RECIPIENT_EMAILS="investor1@example.com,analyst2@example.com"

# Highly Recommended
REDDIT_CLIENT_ID="your_client_id"
REDDIT_CLIENT_SECRET="your_secret"
ECOS_API_KEY="your_ecos_key"
FMP_API_KEY="your_fmp_key"

# Optional
# TAVILY_API_KEY="your_tavily_key"

# Monitoring
MONITOR_FULL_CONTENT=true

# User Agent
USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### Security Best Practices

**NEVER commit `.env` file to version control**

- `.env` is already in `.gitignore`
- Use environment variables for all secrets
- Rotate API keys periodically

**Gmail Security**:

- Requires 2-factor authentication enabled
- Use app-specific password (not your main password)
- Revoke if compromised

**API Key Exposure**:

- Monitoring logs may contain partial API responses
- Set `MONITOR_FULL_CONTENT=false` for production
- Store logs in secure location

---

## Usage

### Manual Mode (Single Stock Analysis)

Analyze a specific stock ticker immediately:

```bash
# Analyze US stock
python main.py AAPL

# Analyze Korean stock (6-digit code)
python main.py 005930  # Samsung Electronics

# Analyze crypto-related stock
python main.py COIN
```

**Behavior**:

- Analyzes specified ticker immediately
- Does not affect ticker queue
- Completes in ~25-30 minutes
- Sends PDF report via email

### Cron Mode (Automated Daily Execution)

Set up automated analysis for multiple stocks:

#### 1. Create Ticker Queue

```bash
# Create ticker queue file
echo "AAPL" >> ticker_queue.txt
echo "GOOGL" >> ticker_queue.txt
echo "MSFT" >> ticker_queue.txt
echo "005930" >> ticker_queue.txt  # Samsung Electronics
echo "035720" >> ticker_queue.txt  # Kakao
```

#### 2. Run Without Arguments

```bash
# Processes next unanalyzed ticker from queue
python main.py
```

**Behavior**:

- Reads `ticker_queue.txt`
- Checks `analyzed_tickers.json` for completion status
- Analyzes next unanalyzed ticker
- Marks ticker as analyzed (won't re-analyze)
- On failure: Ticker remains unanalyzed for next run

#### 3. Setup Daily Cron Job

**Unix/Linux/macOS**:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM)
0 9 * * * cd /path/to/jookkoomi && /path/to/venv/bin/python main.py >> cron.log 2>&1

# Alternative: Weekdays only at 6 AM (before market open)
0 6 * * 1-5 cd /path/to/jookkoomi && /path/to/venv/bin/python main.py >> cron.log 2>&1
```

**Windows (Task Scheduler)**:

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 9:00 AM
4. Action: Start a program
5. Program: `C:\path\to\jookkoomi\venv\Scripts\python.exe`
6. Arguments: `main.py`
7. Start in: `C:\path\to\jookkoomi`

### Queue Management

Check queue status and manage analyzed tickers:

```bash
# Check current queue status
cat ticker_queue.txt

# View analyzed tickers
cat analyzed_tickers.json

# Reset ticker for re-analysis
# (manually edit analyzed_tickers.json and remove the ticker entry)

# Add new ticker to queue
echo "NVDA" >> ticker_queue.txt
```

### Understanding Execution Modes

| Mode       | Command                 | Trigger                | Queue Impact           | Use Case                     |
| ---------- | ----------------------- | ---------------------- | ---------------------- | ---------------------------- |
| **Manual** | `python main.py TICKER` | Explicit ticker        | None (queue unchanged) | Ad-hoc analysis, research    |
| **Cron**   | `python main.py`        | Next unanalyzed ticker | Marks as analyzed      | Daily automation, monitoring |

---

## Architecture

### Technology Stack

- **Framework**: LangGraph (state-based agent orchestration)
- **AI Brain**: Google Gemini 2.5 Pro (with experimental thinking mode)
- **Report Formatting**: Google Gemini 2.5 Flash
- **Data Collection**: 14 specialized tools (see [Tools](#tools--data-sources) section)
- **Report Generation**: markdown-pdf (converts markdown to PDF)
- **Email Delivery**: SMTP via Gmail
- **Monitoring**: Custom execution tracking with token counting and cost calculation
- **Queue System**: File-based with atomic operations and file locking

### Execution Flow

```
User Input (Ticker)
    ↓
Main Graph (graph.py)
    ↓
dispatch_parallel_groups (Sequential Execution with API Rate Limiting)
    ├─→ Fundamental Subgraph (Parts 1-5)   → 90s delay
    ├─→ Technical Subgraph (Parts 6-8)     → 90s delay
    ├─→ Sentiment Subgraph (Parts 9-11)    → 90s delay
    └─→ Macro Subgraph (Parts 12-15)
    ↓
combine_results (Merge all sections)
    ↓
outlook_analysis (Part 16: Synthesis)  → 90s delay
    ↓
unify_report (Format standardization)  → 90s delay
    ↓
translate_report (Korean translation - optional)
    ↓
generate_and_send_report (PDF + Email)
    ↓
Email Inbox (Multiple recipients)
```

### Key Design Decisions

**Sequential Group Execution**

- Groups execute one after another (not in parallel)
- 90-second delays between groups prevent API rate limit exhaustion
- Balances throughput with API quota management

**Automatic Retry Logic**

- Failed groups are retried once with exponential backoff
- Partial reports generated if some groups fail
- Errors logged to monitoring system for debugging

**Graceful Degradation**

- Missing optional API keys: System generates partial reports
- Tool execution failures: Analysis continues with available data
- Network issues: Retry logic prevents total failure

**File-Based Queue System**

- `ticker_queue.txt`: List of tickers to analyze
- `analyzed_tickers.json`: Completion tracking with timestamps
- `.ticker_queue.lock`: Prevents concurrent execution
- Thread-safe atomic operations

---

## Analysis Workflow

JooKkoomi executes a comprehensive 16-stage analysis workflow grouped into 4 categories:

### Group 1: Fundamental Analysis (Parts 1-5)

| Part  | Title                        | Key Analysis Areas                                                       |
| ----- | ---------------------------- | ------------------------------------------------------------------------ |
| **1** | Financial Statement Analysis | Vertical analysis, financial ratios, profitability, solvency, liquidity  |
| **2** | Industry Status Analysis     | Market positioning, competitive landscape, industry trends, market share |
| **3** | Competitive Analysis         | Porter's Five Forces, competitor comparison, differentiation factors     |
| **4** | Management Quality           | Leadership assessment, governance structure, strategic vision            |
| **5** | Growth Potential             | Revenue projections, expansion plans, innovation pipeline, R&D           |

**Tools Used**: `get_financial_data`, `get_historical_data`, `tavily_search`, `google_news_search`

---

### Group 2: Technical Analysis (Parts 6-8)

| Part  | Title                   | Key Analysis Areas                                                  |
| ----- | ----------------------- | ------------------------------------------------------------------- |
| **6** | Price & Volume Analysis | Historical price trends, support/resistance levels, volume patterns |
| **7** | Technical Indicators    | Moving averages, RSI, MACD, Bollinger Bands, momentum signals       |
| **8** | Chart Patterns          | Trend analysis, candlestick patterns, breakout signals              |

**Tools Used**: `get_ta_data`, `get_historical_data`

---

### Group 3: Sentiment Analysis (Parts 9-11)

| Part   | Title                  | Key Analysis Areas                                                   |
| ------ | ---------------------- | -------------------------------------------------------------------- |
| **9**  | Market Sentiment       | Fear & Greed Index, insider trading activity, institutional holdings |
| **10** | News Analysis          | Recent headlines, analyst ratings, corporate announcements           |
| **11** | Social Media Sentiment | Reddit discussions, Google Trends, retail investor mood              |

**Tools Used**: `get_market_sentiment`, `get_guidance`, `scrap_reddit`, `google_news_search`, `get_consumer_trends`

---

### Group 4: Macroeconomic Analysis (Parts 12-15)

| Part   | Title               | Key Analysis Areas                                                         |
| ------ | ------------------- | -------------------------------------------------------------------------- |
| **12** | Economic Indicators | GDP, unemployment, inflation, leading indicators                           |
| **13** | Global Environment  | International trade, currency movements, geopolitical factors, FOMC policy |
| **14** | Policy Environment  | Fiscal policy, regulatory changes, government initiatives                  |
| **15** | Economic Cycle      | Current phase, recession indicators, sectoral rotation                     |

**Tools Used**: `get_economic_indicator`, `get_global_environment`, `get_policy_environment`, `get_economic_cycle`, `get_fomc`, `get_consumer_trends`

---

### Part 16: Comprehensive Synthesis

**Investment Recommendation**: Integrates all 15 analyses to provide:

- Overall investment rating (BUY/HOLD/SELL)
- Target price estimation
- Risk assessment and mitigation strategies
- Trading strategy recommendations
- Timeline for investment thesis

**Tools Used**: None (pure AI synthesis of all previous analyses)

---

### Execution Timeline

**Total Time**: ~25-30 minutes per stock

**Breakdown**:

- Fundamental Group (Parts 1-5): ~8 minutes + 90s delay
- Technical Group (Parts 6-8): ~5 minutes + 90s delay
- Sentiment Group (Parts 9-11): ~5 minutes + 90s delay
- Macro Group (Parts 12-15): ~7 minutes
- Part 16 Synthesis: ~3 minutes (after 90s delay)
- Report Formatting: ~2 minutes (after 90s delay)
- Korean Translation: ~2 minutes (optional)

**Note**: Each part is AI-generated based on real-time data, not templated responses.

---

## Tools & Data Sources

JooKkoomi integrates **14 specialized tools** across **7 categories**:

### Tool Registry

| Category      | Tool Name                | Purpose                                      | Data Source                   | Used In Parts |
| ------------- | ------------------------ | -------------------------------------------- | ----------------------------- | ------------- |
| **Financial** | `get_financial_data`     | Financial statements, ratios, fundamentals   | yfinance, SEC EDGAR           | 1, 2, 5       |
| **Financial** | `get_historical_data`    | Price history, volume, splits, dividends     | yfinance, pykrx               | 1, 6, 7       |
| **Search**    | `tavily_search`          | Real-time web search for news/events         | Tavily API                    | 2, 3, 10      |
| **Search**    | `google_news_search`     | Recent news headlines and articles           | GoogleNews, newspaper3k       | 2, 10         |
| **Sentiment** | `get_market_sentiment`   | Fear & Greed Index, institutional data       | finvizfinance, fear-and-greed | 9             |
| **Sentiment** | `scrap_reddit`           | Social media discussions and sentiment       | Reddit API (praw)             | 11            |
| **Technical** | `get_ta_data`            | Technical indicators (RSI, MACD, etc.)       | ta library, yfinance          | 7, 8          |
| **Guidance**  | `get_guidance`           | Analyst ratings, price targets, forecasts    | yfinance, FMP                 | 9, 10         |
| **Macro**     | `get_economic_indicator` | US macro data (GDP, CPI, unemployment)       | FRED (pandas-datareader)      | 12, 15        |
| **Macro**     | `get_global_environment` | International trade, currency, commodities   | yfinance, FRED                | 13            |
| **Macro**     | `get_policy_environment` | Fiscal/monetary policy indicators            | FRED, ECOS                    | 14            |
| **Macro**     | `get_economic_cycle`     | Business cycle indicators, recession signals | FRED                          | 15            |
| **Macro**     | `get_fomc`               | Federal Reserve policy, interest rates       | FRED                          | 13            |
| **Trends**    | `get_consumer_trends`    | Consumer interest, search trends             | Google Trends (pytrends)      | 11, 13        |

### Data Source Reliability

- **Tier 1 (Official)**: SEC EDGAR, FRED (Federal Reserve), Bank of Korea ECOS
- **Tier 2 (Established)**: Yahoo Finance, Reddit API, Google Trends
- **Tier 3 (Third-party)**: finvizfinance, FMP, Tavily, GoogleNews

### Rate Limiting

- **90-second delays** between analysis groups prevent API quota exhaustion
- Free tier limits: Gemini (50 requests/day), Reddit (60 requests/minute), FRED (unlimited)
- Paid tier recommended for daily automation

---

## Monitoring & Cost Tracking

### Execution Monitoring

Every analysis run generates comprehensive monitoring logs for transparency and debugging.

**Log Location**: `./monitoring_logs/TICKER_RUN-ID_execution_log.json`

**Tracked Metrics**:

- **Execution Timeline**: Start/end timestamps for each node and subgraph
- **LLM Usage**: Token counts (input/output), model names, response times
- **Tool Executions**: Arguments, results, latency for all 14 tools
- **Cost Breakdown**: Real-time USD cost calculation (Gemini pricing)
- **Error Tracking**: Exceptions, tracebacks, retry attempts
- **State Evolution**: Snapshots of agent state at key checkpoints

### Cost Calculation

**Estimated Cost Per Analysis**: $0.30 - $0.80 USD

**Breakdown** (based on Gemini 2.5 Pro pricing):

- Input tokens: ~40,000-60,000 tokens (~$0.20-0.30)
- Output tokens: ~10,000-15,000 tokens (~$0.10-0.20)
- Report formatting (Flash): ~$0.05-0.10
- Korean translation (Flash): ~$0.05-0.10

**Monthly Budget**:

- Daily analysis of 30 stocks: ~$15-24/month
- Daily analysis of 40 stocks: ~$20-32/month

**External API Costs**:

- Most data sources are free (yfinance, FRED, Reddit, Google Trends)
- Optional paid services: Tavily ($50/mo), FMP ($14-29/mo)

### Cost Control

**Reduce Costs**:

```env
# Reduce log file size (1MB → 500KB per run)
MONITOR_FULL_CONTENT=false
```

**Track Costs**:

```bash
# View cost summary in monitoring log
cat monitoring_logs/AAPL_*_execution_log.json | grep "cost_summary"
```

**Example Cost Summary**:

```json
{
  "cost_summary": {
    "total_cost_usd": 0.52,
    "total_tokens": {
      "input": 45230,
      "output": 12450,
      "total": 57680
    },
    "llm_calls": 48,
    "tool_calls": 67,
    "gemini_2_5_pro_calls": 32,
    "gemini_2_5_flash_calls": 16
  }
}
```

---

## Troubleshooting

### Common Issues and Solutions

| Issue                             | Cause                          | Solution                                         |
| --------------------------------- | ------------------------------ | ------------------------------------------------ |
| **`No API key found`**            | Missing `.env` file            | Copy `.env.example` to `.env` and fill in keys   |
| **`Gmail authentication failed`** | Wrong app password             | Generate new app password (requires 2FA enabled) |
| **`Group execution failed`**      | API quota exceeded             | Check API limits, increase delays in `graph.py`  |
| **`Empty PDF generated`**         | All analysis parts failed      | Check monitoring log for errors, verify API keys |
| **`Queue locked`**                | Previous run crashed           | Delete `.ticker_queue.lock` file                 |
| **`Korean translation missing`**  | Missing `GOOGLE_API_KEY_FLASH` | Add second Gemini API key or accept English-only |
| **`Tool execution timeout`**      | Network issues                 | Retry analysis, check internet connection        |
| **`ModuleNotFoundError`**         | Dependencies not installed     | Run `pip install -r requirements.txt`            |
| **`No tickers available`**        | Empty queue or all analyzed    | Add tickers to `ticker_queue.txt`                |

### Debug Mode

Enable detailed logging for troubleshooting:

```env
# In .env file
MONITOR_FULL_CONTENT=true
```

Then run analysis and check logs:

```bash
python main.py AAPL
cat monitoring_logs/AAPL_*_execution_log.json
```

### Getting Help

1. **Check monitoring logs**: `./monitoring_logs/` directory
2. **Review error messages**: Console output during execution
3. **Verify API keys**: Ensure all required keys in `.env` file
4. **Validate ticker symbol**: Use Yahoo Finance to verify ticker exists
5. **Check internet connection**: All tools require network access
6. **Review API quotas**: Gemini free tier has daily limits

### Manual Queue Reset

If `analyzed_tickers.json` becomes corrupted:

```bash
# Backup current state
cp analyzed_tickers.json analyzed_tickers.json.backup

# Reset (delete file - will be recreated)
rm analyzed_tickers.json

# Or manually edit to remove specific ticker
```

---

## Advanced Usage

### Queue Management Deep Dive

**analyzed_tickers.json Structure**:

```json
{
  "version": "1.0",
  "last_updated": "2025-12-08T15:30:00",
  "tickers": [
    {
      "ticker": "AAPL",
      "status": "completed",
      "analysis_date": "2025-12-08",
      "completion_time": "2025-12-08T15:30:00",
      "run_id": "abc-123-def",
      "monitoring_log": "./monitoring_logs/AAPL_abc-123-def_execution_log.json"
    }
  ]
}
```

**Manual Ticker Reset**:

```bash
# Open analyzed_tickers.json and remove the ticker entry
# Or delete the entire file to reset all tickers
rm analyzed_tickers.json
```

### Custom Cron Schedules

```bash
# Every weekday at 6 AM (before market open)
0 6 * * 1-5 cd /path/to/jookkoomi && /path/to/venv/bin/python main.py >> cron.log 2>&1

# Every 4 hours during trading hours
0 9,13,17 * * * cd /path/to/jookkoomi && /path/to/venv/bin/python main.py >> cron.log 2>&1

# Twice daily (morning and evening)
0 6,18 * * * cd /path/to/jookkoomi && /path/to/venv/bin/python main.py >> cron.log 2>&1
```

### Customization Points

**Adjust API Rate Limiting**:

```python
# In graph.py, modify GROUP_DELAYS
GROUP_DELAYS = {
    "fundamental": 60,   # Reduce from 90s to 60s
    "technical": 60,
    "sentiment": 60,
    "macro": 0
}
```

**Customize Analysis Prompts**:

- Edit `prompts.py` to modify analysis methodology
- Change `PART_TITLES` to adjust section headings
- Modify `NEEDED_TOOLS` to use different data sources

**Add New Tools**:

1. Create new tool function in `tools/` directory
2. Add to tool registry in `tools/__init__.py`
3. Update `prompts.py` NEEDED_TOOLS for relevant parts
4. Bind tool to LLM in `llm.py`

**Customize Email Template**:

- Edit `reporter.py` to modify email subject/body
- Change PDF generation settings
- Add custom headers or footers

### Performance Optimization

**Reduce Execution Time**:

- Decrease delays in `graph.py` (if you have higher API quotas)
- Disable Korean translation (saves 2-3 minutes)
- Use Gemini 2.5 Flash instead of Pro (trades quality for speed)

**Reduce Costs**:

```env
# Reduce log file size
MONITOR_FULL_CONTENT=false

# Use only free data sources (disable FMP, Tavily)
# FMP_API_KEY=""
# TAVILY_API_KEY=""
```

**Improve Reliability**:

- Increase retry attempts in `graph.py` `dispatch_parallel_groups()`
- Add error notifications via email
- Implement backup LLM providers

---

## System Requirements

### Minimum Requirements

- **Python**: 3.10 or higher
- **RAM**: 4 GB
- **Disk Space**: 1 GB free (for reports and logs)
- **Internet**: Stable connection (API-dependent)
- **OS**: macOS, Linux, Windows (WSL recommended for cron)

### Recommended Requirements

- **Python**: 3.11+
- **RAM**: 8 GB (for large monitoring logs)
- **Disk Space**: 5 GB free (reports accumulate over time)
- **Internet**: High-speed connection (reduces execution time)

### Compatibility

- ✅ **macOS** (10.15+)
- ✅ **Linux** (Ubuntu 20.04+, CentOS 8+)
- ✅ **Windows 10/11** (WSL recommended for cron)
- ⚠️ **Windows without WSL** (manual mode only, no cron)

---

## Important Disclaimers

### ⚖️ NOT FINANCIAL ADVICE

**This software is for informational and educational purposes only.** JooKkoomi's analysis does not constitute professional financial, investment, or trading advice.

- **Do your own research**: Always verify AI-generated insights with independent sources
- **Past performance ≠ future results**: Historical data does not predict future outcomes
- **Markets are unpredictable**: AI cannot foresee black swan events or market anomalies
- **Consult professionals**: Speak with licensed financial advisors before making investment decisions
- **Use at your own risk**: Authors and contributors assume no liability for investment losses

### Known Limitations

- **AI Hallucinations**: LLMs may generate plausible but incorrect information - always verify critical facts
- **Data Lag**: Real-time data not guaranteed; some sources may have delays
- **Model Bias**: LLM training data has a cutoff date; recent events may not be reflected
- **API Dependencies**: External service outages affect analysis quality
- **Korean Stock Coverage**: Limited by data availability compared to US stocks

### Execution Time Expectations

**Average Runtime**: 25-30 minutes per stock

**Why so slow?**

- API rate limiting (90-second delays prevent quota exhaustion)
- LLM thinking time (Gemini 2.5 Pro extended thinking mode)
- 14 tool executions with network latency
- Comprehensive analysis (not a quick price lookup)

**This is not a real-time trading tool** - Use for research and strategic planning, not day trading.

### Ethical Use

- Respect API rate limits and terms of service
- Do not use for market manipulation or insider trading
- Attribute data sources appropriately
- Comply with securities regulations in your jurisdiction

---

## Contributing

Contributions are welcome! If you'd like to improve JooKkoomi:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Areas for Contribution**:

- Additional data source integrations
- New analysis methodologies
- Performance optimizations
- Documentation improvements
- Bug fixes and error handling

---

## License

License to be determined - please check back later.

---

## Acknowledgments

- **LangGraph Team** at LangChain for the agent orchestration framework
- **Google Gemini API** for advanced AI capabilities
- **Open-source data providers**: yfinance, FRED, Reddit API, Google Trends
- **Community contributors** who have helped improve this project

---

## Project Structure

```
jookkoomi-public/
├── main.py                      # Entry point (CLI handler, async orchestrator)
├── graph.py                     # Main workflow graph (16 parts)
├── subgraph.py                  # Group-specific subgraphs (F/T/S/M)
├── state.py                     # AgentState and GroupWorkerState schemas
├── llm.py                       # LLM initialization (Gemini models)
├── prompts.py                   # 16 part analysis prompts (47KB)
├── reporter.py                  # PDF generation and email sending
├── config_email.py              # Email configuration loader
├── ticker_queue_manager.py      # Queue management system
├── requirements.txt             # Python dependencies (48 packages)
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
├── ticker_queue.txt             # Ticker queue (user-managed)
├── analyzed_tickers.json        # Analysis tracking (auto-generated)
│
├── tools/                       # 14 analysis tools
│   ├── __init__.py             # Tool registry
│   ├── financial.py            # Financial data tools
│   ├── search.py               # Web search tools
│   ├── sentiment.py            # Sentiment analysis tools
│   ├── technical.py            # Technical analysis tools
│   ├── guidance.py             # Analyst guidance tools
│   ├── macro.py                # Macroeconomic tools
│   ├── macro_config.py         # Macro tool configuration
│   └── trends.py               # Consumer trends tools
│
├── utils/                       # Utility functions
│   ├── __init__.py
│   ├── text_cleaning.py        # Text processing utilities
│   └── retry.py                # Retry logic
│
├── monitoring/                  # Execution tracking
│   ├── __init__.py
│   ├── core.py                 # MonitoringContext
│   ├── decorators.py           # Monitoring decorators
│   ├── cost_calculator.py      # Cost estimation
│   ├── token_counter.py        # Token usage tracking
│   ├── serializers.py          # JSON serialization
│   ├── writer.py               # Log file writing
│   └── cleanup.py              # Log cleanup utilities
│
├── monitoring_logs/             # Execution logs (auto-generated)
└── reports/                     # Generated PDF reports (auto-generated)
```

---

## Quick Reference

### Common Commands

```bash
# Analyze single stock (manual mode)
python main.py AAPL

# Process next ticker from queue (cron mode)
python main.py

# Check queue contents
cat ticker_queue.txt

# View analyzed tickers
cat analyzed_tickers.json

# Add ticker to queue
echo "NVDA" >> ticker_queue.txt

# Clear queue lock (if stuck)
rm .ticker_queue.lock

# View monitoring logs
ls -lh monitoring_logs/

# Check latest log
cat monitoring_logs/$(ls -t monitoring_logs/ | head -1)
```

### Environment Variables Cheat Sheet

| Variable               | Required?      | Purpose                        |
| ---------------------- | -------------- | ------------------------------ |
| `GOOGLE_API_KEY`       | ✅ Yes         | Gemini 2.5 Pro (main analysis) |
| `GOOGLE_API_KEY_FLASH` | ✅ Yes         | Gemini 2.5 Flash (formatting)  |
| `GMAIL_USER`           | ✅ Yes         | Email sender                   |
| `GMAIL_APP_PASSWORD`   | ✅ Yes         | Email authentication           |
| `RECIPIENT_EMAILS`     | ✅ Yes         | Report recipients              |
| `REDDIT_CLIENT_ID`     | ⚠️ Recommended | Social sentiment               |
| `REDDIT_CLIENT_SECRET` | ⚠️ Recommended | Social sentiment               |
| `ECOS_API_KEY`         | ⚠️ Recommended | Korean macro data              |
| `FMP_API_KEY`          | ⚠️ Recommended | Enhanced financials            |
| `TAVILY_API_KEY`       | ⭕ Optional    | Web search                     |
| `MONITOR_FULL_CONTENT` | ⭕ Optional    | Log detail level               |

---

**Built with LangGraph, powered by Gemini 2.5 Pro**

For questions or support, please open an issue in the repository.
