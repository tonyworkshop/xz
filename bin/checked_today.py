#!/usr/bin/env python3
"""人工确认已检查，重置告警基准日期"""

from datetime import date
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
LAST_CHECK_FILE = OUTPUT_DIR / "last_check_date"
ALERT_COUNT_FILE = OUTPUT_DIR / ".alert_count"


def main():
    today = date.today().isoformat()
    LAST_CHECK_FILE.write_text(today)
    print(f"[确认] 已记录检查日期: {today}")

    if ALERT_COUNT_FILE.exists():
        ALERT_COUNT_FILE.unlink()
        print("[信息] 告警计数器已清零")


if __name__ == "__main__":
    main()
