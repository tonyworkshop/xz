#!/usr/bin/env python3
"""检查抓取结果，连续无更新时发送 Slack 告警"""

import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ALERT_COUNT_FILE = PROJECT_ROOT / "output" / ".alert_count"
LAST_CHECK_FILE = PROJECT_ROOT / "output" / "last_check_date"
SLACK_SEND_SCRIPT = Path.home() / "dev" / "bin" / "slack-send.py"
MAX_ALERTS = 10
ALERT_THRESHOLD_DAYS = 3


def get_last_real_update_date() -> date | None:
    """从 git log 中找到最后一次有真实更新的 commit 日期"""
    result = subprocess.run(
        ["git", "log", "--format=%ai %s", "-200"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    for line in result.stdout.splitlines():
        if re.search(r'\+([1-9]\d*)\s+topics', line) or re.search(r'\+([1-9]\d*)\s+comments', line):
            # 日期格式: 2026-03-16 01:43:00 +0800 auto: update ...
            date_str = line[:10]
            return date.fromisoformat(date_str)
    return None


def read_last_check_date() -> date | None:
    """读取人工确认的日期"""
    try:
        return date.fromisoformat(LAST_CHECK_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def has_real_updates_recently() -> bool:
    """检查是否需要告警：以最后真实更新日期和人工确认日期中较晚者为基准"""
    last_update = get_last_real_update_date()
    last_check = read_last_check_date()

    # 取两者中较晚的日期作为 baseline
    candidates = [d for d in (last_update, last_check) if d is not None]
    if not candidates:
        return False  # 无任何记录，触发告警

    baseline = max(candidates)
    days_since = (date.today() - baseline).days
    return days_since < ALERT_THRESHOLD_DAYS


def read_alert_count() -> int:
    try:
        return int(ALERT_COUNT_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_alert_count(count: int):
    ALERT_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_COUNT_FILE.write_text(str(count))


def send_slack_dm(message: str) -> bool:
    """通过统一的 slack-send.py 发送 DM"""
    try:
        result = subprocess.run(
            [str(SLACK_SEND_SCRIPT), "-m", message],
            capture_output=True,
            text=True,
        )
    except OSError as e:
        print(f"[错误] Slack 请求异常: {e}")
        return False

    if result.returncode == 0:
        print("[成功] Slack 发送成功")
        return True

    error = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
    print(f"[错误] Slack 发送失败: {error}")
    return False


def get_latest_commit_message() -> str:
    """获取最新一条 commit message"""
    result = subprocess.run(
        ["git", "log", "--format=%s", "-1"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT,
    )
    return result.stdout.strip()


def check_fetch_failure():
    """检查最新 commit 是否包含 FETCH FAILED，立即通知（附错误详情）"""
    msg = get_latest_commit_message()
    if "FETCH FAILED" not in msg:
        return
    print(f"[告警] 检测到抓取失败: {msg}")
    error_detail = ""
    error_file = PROJECT_ROOT / "output" / "last_error.txt"
    if error_file.exists():
        error_detail = "\n" + error_file.read_text().strip()
    send_slack_dm(f"⚠️ 知识星球抓取失败\ncommit: {msg}{error_detail}")


def main():
    # 检查 fetch 失败（立即通知）
    check_fetch_failure()

    # 检查连续无数据更新（3天阈值）
    if has_real_updates_recently():
        if ALERT_COUNT_FILE.exists():
            ALERT_COUNT_FILE.unlink()
            print("[信息] 检测到真实更新，告警计数器已清零")
        else:
            print("[信息] 最近 3 天有真实数据更新，无需告警")
        return

    count = read_alert_count()
    if count >= MAX_ALERTS:
        print(f"[信息] 已达到最大告警次数 ({MAX_ALERTS})，停止发送")
        return

    count += 1
    msg = f"⚠️ 知识星球抓取连续 3 天无真实数据更新（第 {count}/{MAX_ALERTS} 次告警）\n请检查登录状态是否过期。"
    print(f"[告警] {msg}")
    send_slack_dm(msg)
    write_alert_count(count)


if __name__ == "__main__":
    main()
