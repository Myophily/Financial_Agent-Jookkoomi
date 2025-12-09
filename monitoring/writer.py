# monitoring/writer.py

"""
JSON file writer for monitoring logs.
Organizes logs by date and creates timestamped filenames.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class MonitoringWriter:
    """
    Handles writing monitoring data to JSON files with date-based organization.

    File naming convention:
        jookoomi_{ticker}_{YYYYMMDD}_{HHMMSS}_{run_id_short}.json

    Directory structure:
        ./monitoring_logs/
        ├── 2025-11-30/
        │   ├── jookoomi_005930_20251130_142345_a1b2c3d4.json
        │   └── ...
        └── 2025-11-29/
            └── ...
    """

    def __init__(self, log_dir: str, ticker: str, run_id: str):
        """
        Initialize monitoring writer.

        Args:
            log_dir: Base directory for logs (e.g., "./monitoring_logs")
            ticker: Stock ticker being analyzed
            run_id: UUID for this run
        """
        self.log_dir = Path(log_dir)
        self.ticker = ticker
        self.run_id = run_id

        # Create date-based subdirectory (YYYY-MM-DD)
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = self.log_dir / date_str
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp_date = datetime.now().strftime("%Y%m%d")
        timestamp_time = datetime.now().strftime("%H%M%S")
        run_id_short = run_id.split('-')[0]  # First segment of UUID
        self.filename = f"jookoomi_{ticker}_{timestamp_date}_{timestamp_time}_{run_id_short}.json"
        self.filepath = self.output_dir / self.filename

    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write monitoring data to JSON file.

        Args:
            data: Complete monitoring data dictionary

        Returns:
            True if write successful, False otherwise
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Calculate file size
            file_size_mb = self.filepath.stat().st_size / 1024 / 1024

            print(f"\n{'=' * 80}")
            print(f"📊 Monitoring Log Saved")
            print(f"{'=' * 80}")
            print(f"   Location: {self.filepath}")
            print(f"   File size: {file_size_mb:.2f} MB")
            print(f"   Run ID: {self.run_id}")
            print(f"{'=' * 80}\n")

            return True

        except Exception as e:
            print(f"\n{'=' * 80}")
            print(f"❌ Failed to Write Monitoring Log")
            print(f"{'=' * 80}")
            print(f"   Error: {e}")
            print(f"   Attempted path: {self.filepath}")
            print(f"{'=' * 80}\n")

            import traceback
            traceback.print_exc()

            return False
