# ticker_queue_manager.py

"""
Ticker Queue Manager for JooKkoomi Cron-Based Daily Analysis

Manages a plain text queue of stock tickers to be analyzed, tracking which
tickers have already been analyzed to support automated daily execution.

Features:
- File-based queue management (ticker_queue.txt)
- JSON-based analysis tracking (analyzed_tickers.json)
- File locking to prevent concurrent execution
- Atomic writes to prevent corruption
- Graceful error handling
"""

import json
import os
import fcntl
from datetime import datetime
from typing import Optional, Dict, List, Set
from pathlib import Path


class TickerQueueManager:
    """
    Manages ticker queue and analysis tracking for automated daily execution.

    Thread-safe file operations with locking to prevent concurrent access issues.
    All operations are atomic to prevent data corruption on failures.
    """

    def __init__(self, base_dir: str):
        """
        Initialize queue manager with base directory.

        Args:
            base_dir: Project root directory (e.g., "/path/to/jookkoomi")
        """
        self.base_dir = Path(base_dir)
        self.queue_file = self.base_dir / "ticker_queue.txt"
        self.tracking_file = self.base_dir / "analyzed_tickers.json"
        self.lock_file = self.base_dir / ".ticker_queue.lock"

    def _acquire_lock(self) -> Optional[int]:
        """
        Acquires exclusive lock on queue operations.

        Prevents concurrent cron runs from processing the same ticker.
        Non-blocking lock - fails immediately if another process holds the lock.

        Returns:
            int: File descriptor of lock file, or None if lock acquisition fails
        """
        try:
            # Open or create lock file
            lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            return lock_fd

        except (IOError, OSError) as e:
            # Lock already held by another process
            return None

    def _release_lock(self, lock_fd: Optional[int]):
        """
        Releases lock and closes file descriptor.

        Args:
            lock_fd: File descriptor from _acquire_lock()
        """
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception as e:
                # Non-critical error, lock will be released when process exits
                print(f"[WARN] Failed to release lock: {e}")

    def get_next_ticker(self) -> Optional[str]:
        """
        Returns the first unanalyzed ticker from the queue.

        Reads ticker_queue.txt and returns the first ticker that hasn't
        been analyzed yet (not in analyzed_tickers.json).

        Returns:
            str: Next ticker to analyze, or None if:
                - Queue file doesn't exist
                - Queue is empty
                - All tickers already analyzed
                - File I/O error occurred
                - Lock acquisition failed

        Example:
            >>> manager = TickerQueueManager("/path/to/JooKkoomi")
            >>> ticker = manager.get_next_ticker()
            >>> if ticker:
            ...     print(f"Analyzing: {ticker}")
            ... else:
            ...     print("No tickers to analyze")
        """
        # Step 1: Check if queue file exists
        if not self.queue_file.exists():
            print(f"[WARN] Queue file not found: {self.queue_file}")
            print(f"[INFO] Create file: echo 'AAPL' > ticker_queue.txt")
            return None

        # Step 2: Acquire lock to prevent concurrent access
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("[WARN] Could not acquire lock (another process may be running)")
            print("[INFO] If no other process is running, delete: .ticker_queue.lock")
            return None

        try:
            # Step 3: Read queue file
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                # Read all lines, strip whitespace, ignore empty lines
                all_tickers = [line.strip() for line in f if line.strip()]

            if not all_tickers:
                print("[INFO] Queue file is empty")
                print(f"[INFO] Add tickers: echo 'AAPL' >> ticker_queue.txt")
                return None

            # Step 4: Get set of already-analyzed tickers
            analyzed_tickers = self.get_analyzed_tickers()

            # Step 5: Find first unanalyzed ticker
            for ticker in all_tickers:
                if ticker not in analyzed_tickers:
                    print(f"[INFO] Next ticker from queue: {ticker}")
                    return ticker

            # All tickers have been analyzed
            print("[INFO] All tickers in queue have been analyzed")
            print(f"[INFO] Total in queue: {len(all_tickers)}")
            print(f"[INFO] Already analyzed: {len(analyzed_tickers)}")
            return None

        except Exception as e:
            print(f"[ERROR] Failed to read queue: {e}")
            return None

        finally:
            # Always release lock
            self._release_lock(lock_fd)

    def mark_ticker_analyzed(
        self,
        ticker: str,
        run_id: str,
        monitoring_log_path: str
    ) -> bool:
        """
        Marks a ticker as analyzed and saves tracking information.

        Updates analyzed_tickers.json with completion metadata including
        timestamp, run ID, and link to monitoring log.

        Args:
            ticker: Stock ticker symbol
            run_id: UUID from MonitoringContext
            monitoring_log_path: Relative path to monitoring log file

        Returns:
            bool: True if successfully marked, False on error

        Example:
            >>> manager = TickerQueueManager("/path/to/JooKkoomi")
            >>> success = manager.mark_ticker_analyzed(
            ...     ticker="AAPL",
            ...     run_id="abc-123-def",
            ...     monitoring_log_path="./monitoring_logs/AAPL_abc-123-def_execution_log.json"
            ... )
        """
        # Step 1: Acquire lock
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("[WARN] Could not acquire lock to mark ticker")
            return False

        try:
            # Step 2: Load existing tracking data (or create new)
            if self.tracking_file.exists():
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    tracking_data = json.load(f)
            else:
                # First time - create new tracking structure
                tracking_data = {
                    "version": "1.0",
                    "last_updated": None,
                    "tickers": []
                }

            # Step 3: Create new entry
            new_entry = {
                "ticker": ticker,
                "status": "completed",
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "completion_time": datetime.now().isoformat(),
                "run_id": run_id,
                "monitoring_log": monitoring_log_path
            }

            # Step 4: Add entry and update timestamp
            tracking_data["tickers"].append(new_entry)
            tracking_data["last_updated"] = datetime.now().isoformat()

            # Step 5: Atomic write (write to temp file, then rename)
            temp_file = self.tracking_file.with_suffix(".tmp")

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)

            # Atomic rename (replaces old file safely)
            temp_file.replace(self.tracking_file)

            print(f"[INFO] Marked ticker as analyzed: {ticker}")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to mark ticker: {e}")
            return False

        finally:
            # Always release lock
            self._release_lock(lock_fd)

    def get_analyzed_tickers(self) -> Set[str]:
        """
        Returns set of all analyzed ticker symbols.

        Reads analyzed_tickers.json and extracts all ticker symbols.

        Returns:
            set[str]: Set of ticker symbols (empty set if tracking file doesn't exist)

        Example:
            >>> manager = TickerQueueManager("/path/to/JooKkoomi")
            >>> analyzed = manager.get_analyzed_tickers()
            >>> if "AAPL" in analyzed:
            ...     print("AAPL already analyzed")
        """
        # If tracking file doesn't exist, no tickers analyzed yet
        if not self.tracking_file.exists():
            return set()

        try:
            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)

            # Extract ticker symbols from all entries
            tickers = {entry["ticker"] for entry in tracking_data.get("tickers", [])}
            return tickers

        except Exception as e:
            print(f"[ERROR] Failed to read tracking file: {e}")
            # Return empty set on error (safer to reanalyze than skip)
            return set()

    def get_queue_status(self) -> Dict[str, any]:
        """
        Returns current queue status for monitoring/debugging.

        Provides overview of queue state including counts and next ticker.

        Returns:
            dict: Status information including:
                - total_in_queue: Total tickers in queue file
                - already_analyzed: Count of analyzed tickers
                - remaining: Count of unanalyzed tickers
                - next_ticker: Next ticker to be analyzed (or None)
                - queue_file_exists: Whether queue file exists
                - tracking_file_exists: Whether tracking file exists

        Example:
            >>> manager = TickerQueueManager("/path/to/JooKkoomi")
            >>> status = manager.get_queue_status()
            >>> print(f"Remaining: {status['remaining']}")
        """
        status = {
            "queue_file_exists": self.queue_file.exists(),
            "tracking_file_exists": self.tracking_file.exists(),
            "total_in_queue": 0,
            "already_analyzed": 0,
            "remaining": 0,
            "next_ticker": None
        }

        # Read queue file
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    all_tickers = [line.strip() for line in f if line.strip()]
                status["total_in_queue"] = len(all_tickers)
            except Exception as e:
                print(f"[ERROR] Failed to read queue file: {e}")

        # Get analyzed count
        analyzed_tickers = self.get_analyzed_tickers()
        status["already_analyzed"] = len(analyzed_tickers)

        # Calculate remaining
        status["remaining"] = max(0, status["total_in_queue"] - status["already_analyzed"])

        # Get next ticker (without modifying anything)
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    all_tickers = [line.strip() for line in f if line.strip()]

                for ticker in all_tickers:
                    if ticker not in analyzed_tickers:
                        status["next_ticker"] = ticker
                        break
            except Exception as e:
                print(f"[ERROR] Failed to determine next ticker: {e}")

        return status

    def reset_ticker(self, ticker: str) -> bool:
        """
        Removes a ticker from analyzed tracking (for manual re-analysis).

        Useful when you want to re-analyze a ticker that was previously analyzed.
        Removes all entries for the specified ticker from analyzed_tickers.json.

        Args:
            ticker: Stock ticker symbol to reset

        Returns:
            bool: True if successfully reset, False if not found or error

        Example:
            >>> manager = TickerQueueManager("/path/to/JooKkoomi")
            >>> manager.reset_ticker("AAPL")  # Allow AAPL to be analyzed again
            True
        """
        # Acquire lock
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("[WARN] Could not acquire lock to reset ticker")
            return False

        try:
            # Load tracking data
            if not self.tracking_file.exists():
                print(f"[INFO] Tracking file doesn't exist - nothing to reset")
                return False

            with open(self.tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)

            # Filter out entries for this ticker
            original_count = len(tracking_data["tickers"])
            tracking_data["tickers"] = [
                entry for entry in tracking_data["tickers"]
                if entry["ticker"] != ticker
            ]
            new_count = len(tracking_data["tickers"])

            # Check if any entries were removed
            if original_count == new_count:
                print(f"[INFO] Ticker '{ticker}' not found in tracking file")
                return False

            # Update timestamp
            tracking_data["last_updated"] = datetime.now().isoformat()

            # Atomic write
            temp_file = self.tracking_file.with_suffix(".tmp")

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.tracking_file)

            removed_count = original_count - new_count
            print(f"[INFO] Reset ticker '{ticker}' ({removed_count} entries removed)")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to reset ticker: {e}")
            return False

        finally:
            # Always release lock
            self._release_lock(lock_fd)


# CLI utility functions for manual queue management
if __name__ == "__main__":
    """
    Command-line interface for queue management.

    Usage:
        python ticker_queue_manager.py status        # Show queue status
        python ticker_queue_manager.py next          # Show next ticker
        python ticker_queue_manager.py reset TICKER  # Reset ticker for re-analysis
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ticker_queue_manager.py status")
        print("  python ticker_queue_manager.py next")
        print("  python ticker_queue_manager.py reset TICKER")
        sys.exit(1)

    # Initialize manager with current directory
    manager = TickerQueueManager(".")
    command = sys.argv[1].lower()

    if command == "status":
        # Show queue status
        status = manager.get_queue_status()
        print("\n=== Queue Status ===")
        print(f"Queue file exists: {status['queue_file_exists']}")
        print(f"Tracking file exists: {status['tracking_file_exists']}")
        print(f"Total in queue: {status['total_in_queue']}")
        print(f"Already analyzed: {status['already_analyzed']}")
        print(f"Remaining: {status['remaining']}")
        print(f"Next ticker: {status['next_ticker']}")
        print()

    elif command == "next":
        # Show next ticker
        next_ticker = manager.get_next_ticker()
        if next_ticker:
            print(f"\nNext ticker: {next_ticker}\n")
        else:
            print("\nNo tickers available\n")

    elif command == "reset":
        # Reset ticker
        if len(sys.argv) < 3:
            print("Error: Ticker symbol required")
            print("Usage: python ticker_queue_manager.py reset TICKER")
            sys.exit(1)

        ticker = sys.argv[2].upper()
        success = manager.reset_ticker(ticker)

        if success:
            print(f"\nSuccess: Ticker '{ticker}' reset for re-analysis\n")
        else:
            print(f"\nFailed to reset ticker '{ticker}'\n")

    else:
        print(f"Unknown command: {command}")
        print("Valid commands: status, next, reset")
        sys.exit(1)
