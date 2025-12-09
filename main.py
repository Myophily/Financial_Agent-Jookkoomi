# main.py

import sys
import uuid
import asyncio
from datetime import datetime
from typing import List

from graph import app
from monitoring.core import MonitoringContext
from config_email import load_recipient_emails
from ticker_queue_manager import TickerQueueManager
from pathlib import Path

async def run_analysis():
    """
    Main async function to run the JooKkoomi analysis agent.
    Accepts stock ticker from terminal and executes the workflow graph.
    """

    # Get stock ticker from terminal arguments or queue
    # Determine execution mode: cron mode (no args) vs manual mode (with args)
    cron_mode = len(sys.argv) == 1
    manual_mode = len(sys.argv) == 2

    if not cron_mode and not manual_mode:
        print("--- [JooKkoomi Usage] ---")
        print("Cron Mode (automatic):  python main.py")
        print("Manual Mode (specific): python main.py [stock_ticker]")
        print("")
        print("Examples:")
        print("  python main.py           # Analyze next ticker from queue")
        print("  python main.py AAPL      # Analyze specific ticker")
        print("  python main.py 005930    # Analyze Samsung Electronics")
        print("")
        print("Note: Set recipient emails in .env file under RECIPIENT_EMAILS")
        print("Format: RECIPIENT_EMAILS=\"email1@example.com,email2@example.com\"")
        print("---")
        return

    # Initialize ticker queue manager
    base_dir = Path(__file__).parent.absolute()
    queue_manager = TickerQueueManager(str(base_dir))

    # Fetch ticker from queue or CLI argument
    if cron_mode:
        print("--- [Cron Mode] Fetching next ticker from queue ---")
        target_stock = queue_manager.get_next_ticker()

        if target_stock is None:
            print("\n[INFO] No tickers available for analysis.")
            print("[INFO] Possible reasons:")
            print("  - Queue file (ticker_queue.txt) doesn't exist")
            print("  - Queue file is empty")
            print("  - All tickers have been analyzed")
            print("")
            print("To add tickers, create or edit: ticker_queue.txt")
            print("Format: One ticker per line (e.g., AAPL)")
            print("")
            print("To re-analyze a ticker:")
            print("  python ticker_queue_manager.py reset TICKER")
            return

        print(f"[CRON] Selected ticker from queue: {target_stock}")

    else:  # manual_mode
        target_stock = sys.argv[1]
        print(f"--- [Manual Mode] Analyzing specified ticker: {target_stock} ---")

    # Load and validate recipient email addresses from .env
    try:
        recipient_emails: List[str] = load_recipient_emails()
    except ValueError as e:
        print(f"Error: {str(e)}")
        return

    # Get current date (format: YYYY-MM-DD)
    current_date = datetime.now().strftime("%Y-%m-%d")

    print(f"--- JooKkoomi Agent Analysis Starting ---")
    print(f"Analysis Date: {current_date}")
    print(f"Target Stock: {target_stock}")
    print(f"Recipient Emails: {', '.join(recipient_emails)}")
    print(f"Execution Mode: {'CRON' if cron_mode else 'MANUAL'}")

    # Prepare initial input values for AgentState (must match state.py schema)
    inputs = {
        "target_stock": target_stock,
        "recipient_emails": recipient_emails,
        "current_date": current_date
    }

    # Initialize monitoring system
    monitor = MonitoringContext(
        ticker=target_stock,
        emails=recipient_emails,
        log_dir="./monitoring_logs"
    )
    monitor.start()

    # Configure LangGraph checkpointer with unique thread ID
    # Recursion limit increased to 100 to accommodate 16-part workflow
    # (each part requires multiple graph iterations for tool calls + analysis)
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        },
        "recursion_limit": 100
    }

    # Execute the workflow graph asynchronously

    try:
        final_state = await app.ainvoke(inputs, config=config)

        # Print final results after reaching END node
        print("\n--- [JooKkoomi] All Analysis Complete ---")
        print("\n--- Final State (Final AgentState) ---")
        print(f"Generated Report Sections: {len(final_state['report_sections'])}")
        print(f"Final Part Number: {final_state['current_part']}")
        print("--- Report Generation and Email Sending Complete ---")

        # Finalize monitoring system (success)
        monitor.finalize(status="completed")

        # Mark ticker as analyzed (cron mode only)
        if cron_mode:
            monitoring_log_relative = f"./monitoring_logs/{target_stock}_{monitor.run_id}_execution_log.json"
            success = queue_manager.mark_ticker_analyzed(
                ticker=target_stock,
                run_id=monitor.run_id,
                monitoring_log_path=monitoring_log_relative
            )

            if success:
                print(f"\n[CRON] Ticker {target_stock} marked as analyzed in queue")
                print(f"[CRON] This ticker will be skipped in future runs")
            else:
                print(f"\n[WARN] Failed to mark ticker as analyzed")
                print(f"[WARN] Ticker may be reprocessed on next cron run")

    except Exception as e:
        # Handle critical errors
        print("\n" + "=" * 80)
        print("⚠️  Critical Error: Unable to Complete Analysis")
        print("=" * 80)
        print(f"Error Message: {str(e)}")
        print(f"Error Type: {type(e).__name__}")

        # Print stack trace for debugging
        import traceback
        print("\nDetailed Stack Trace:")
        traceback.print_exc()

        # Record error in monitoring system
        monitor.record_error(e, context="main_execution")

        # Attempt to send error notification email to users
        print("\nAttempting to send error notification email...")
        try:
            _send_error_notification(recipient_emails, target_stock, str(e))
        except Exception as email_error:
            print(f"Error notification email failed: {email_error}")

        print("\nRecommended Actions:")
        print("1. Check your internet connection")
        print("2. Verify API keys in .env file are correct")
        print("3. Ensure Google Gemini API quota is available")
        print("4. Verify the stock ticker is correct")
        print("5. If problem persists, try again later")
        print("=" * 80)

        # Finalize monitoring system (failure)
        monitor.finalize(status="failed", failure_reason=str(e))

        # Do NOT mark ticker as analyzed on failure
        # Failed tickers remain in queue for automatic retry
        if cron_mode:
            print(f"\n[CRON] Ticker {target_stock} NOT marked as analyzed (due to error)")
            print(f"[CRON] This ticker will be retried on next scheduled run")
            print(f"[CRON] To skip this ticker, manually remove it from ticker_queue.txt")


def _send_error_notification(recipient_emails: List[str], target_stock: str, error_message: str):
    """
    Send error notification email to users when critical error occurs.
    Sends to multiple recipients simultaneously.
    """
    import os
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.utils import formatdate

    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        print("Cannot send error notification email without Gmail credentials.")
        return

    subject = f"[Error] JooKkoomi Analysis Failed: {target_stock}"
    body = f"""
Critical error occurred during JooKkoomi stock analysis.

Analysis Target: {target_stock}
Error Message: {error_message[:500]}

This error may be temporary.
Please try again later or verify stock ticker and API key settings.

If the problem persists, contact system administrator.
"""

    msg = MIMEText(body)
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_emails, msg.as_string())
        print(f"Error notification email sent: {', '.join(recipient_emails)}")
    except Exception as e:
        print(f"Error notification email failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_analysis())
