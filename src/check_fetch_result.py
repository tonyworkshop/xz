#!/usr/bin/env python3
"""检查抓取结果，连续无更新时发送 Slack 告警"""

import json
import re
import subprocess
import urllib.request
from pathlib import Path

ALERT_COUNT_FILE = Path(__file__).parent.parent / "output" / ".alert_count"
SLACK_CONFIG_FILE = Path.home() / "slack_user.json"
MAX_ALERTS = 10


def has_real_updates_recently() -> bool:
    """检查最近 3 天的 commit 中是否有真实数据更新"""
    result = subprocess.run(
        ["git", "log", "--since=3 days ago", "--oneline"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent,
    )
    for line in result.stdout.splitlines():
        # 匹配 +N topics 或 +N comments，N > 0
        if re.search(r'\+([1-9]\d*)\s+topics', line) or re.search(r'\+([1-9]\d*)\s+comments', line):
            return True
    return False


def read_alert_count() -> int:
    try:
        return int(ALERT_COUNT_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_alert_count(count: int):
    ALERT_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_COUNT_FILE.write_text(str(count))


def send_slack_dm(message: str) -> bool:
    """通过 Slack Bot 发送 DM（仅用 urllib，无额外依赖）"""
    try:
        config = json.loads(SLACK_CONFIG_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[警告] 无法读取 {SLACK_CONFIG_FILE}: {e}")
        print(f"消息内容: {message}")
        return False

    token = config.get("SLACK_BOT_TOKEN")
    user_id = config.get("SLACK_USER_ID")
    if not token or not user_id:
        print("[警告] slack_user.json 缺少 SLACK_BOT_TOKEN 或 SLACK_USER_ID")
        return False

    payload = json.dumps({"channel": user_id, "text": message}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                print("[成功] Slack 发送成功")
                return True
            else:
                print(f"[错误] Slack 发送失败: {data.get('error')}")
                return False
    except Exception as e:
        print(f"[错误] Slack 请求异常: {e}")
        return False


def main():
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
