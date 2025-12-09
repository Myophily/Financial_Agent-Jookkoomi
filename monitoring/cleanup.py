#!/usr/bin/env python3
# monitoring/cleanup.py

"""
Automatic log cleanup script for JooKkoomi monitoring logs.
Removes logs older than retention period (default: 90 days).

Usage:
    python monitoring/cleanup.py
    python monitoring/cleanup.py --retention-days 30
    python monitoring/cleanup.py --dry-run
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import argparse


DEFAULT_RETENTION_DAYS = 90


def cleanup_old_logs(log_dir: str = "./monitoring_logs", retention_days: int = DEFAULT_RETENTION_DAYS, dry_run: bool = False):
    """
    Remove monitoring logs older than retention_days.

    Args:
        log_dir: Path to monitoring logs directory
        retention_days: Number of days to keep logs (default: 90)
        dry_run: If True, show what would be deleted without actually deleting
    """
    log_path = Path(log_dir)

    if not log_path.exists():
        print(f"❌ Monitoring logs directory not found: {log_dir}")
        return

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    freed_bytes = 0

    print(f"{'=' * 80}")
    print(f"JooKkoomi Monitoring Logs Cleanup")
    print(f"{'=' * 80}")
    print(f"Log directory: {log_path.absolute()}")
    print(f"Retention policy: {retention_days} days")
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
    if dry_run:
        print(f"Mode: DRY RUN (no files will be deleted)")
    print(f"{'=' * 80}\n")

    print(f"Scanning for directories older than {cutoff_date.strftime('%Y-%m-%d')}...\n")

    for date_dir in sorted(log_path.iterdir()):
        if not date_dir.is_dir():
            continue

        try:
            # Parse directory name as date (YYYY-MM-DD)
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")

            if dir_date < cutoff_date:
                # Calculate size before deletion
                dir_size = sum(f.stat().st_size for f in date_dir.glob('**/*') if f.is_file())

                if dry_run:
                    print(f"  [DRY RUN] Would remove: {date_dir.name} ({dir_size / 1024 / 1024:.2f} MB)")
                else:
                    # Remove directory
                    shutil.rmtree(date_dir)
                    print(f"  ✓ Removed: {date_dir.name} ({dir_size / 1024 / 1024:.2f} MB)")

                removed_count += 1
                freed_bytes += dir_size

        except ValueError:
            # Skip directories that don't match date format
            print(f"  ⚠️  Skipped: {date_dir.name} (not a valid date directory)")
            continue

    print(f"\n{'=' * 80}")
    print(f"Cleanup Summary")
    print(f"{'=' * 80}")
    if dry_run:
        print(f"  Directories that would be removed: {removed_count}")
        print(f"  Space that would be freed: {freed_bytes / 1024 / 1024:.2f} MB")
    else:
        print(f"  Directories removed: {removed_count}")
        print(f"  Space freed: {freed_bytes / 1024 / 1024:.2f} MB")
    print(f"{'=' * 80}\n")


def main():
    """Main entry point for cleanup script."""
    parser = argparse.ArgumentParser(
        description="Cleanup old JooKkoomi monitoring logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitoring/cleanup.py
  python monitoring/cleanup.py --retention-days 30
  python monitoring/cleanup.py --dry-run
  python monitoring/cleanup.py --log-dir /path/to/logs --retention-days 7

Cron Job Setup (daily cleanup at 2 AM):
  0 2 * * * cd /path/to/JooKkoomi && python monitoring/cleanup.py
        """
    )

    parser.add_argument(
        "--log-dir",
        default="./monitoring_logs",
        help="Path to monitoring logs directory (default: ./monitoring_logs)"
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Number of days to keep logs (default: {DEFAULT_RETENTION_DAYS})"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    args = parser.parse_args()

    # Run cleanup
    cleanup_old_logs(args.log_dir, args.retention_days, args.dry_run)


if __name__ == "__main__":
    main()
