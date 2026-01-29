#!/usr/bin/env python3
"""
知识星球 Topics 抓取脚本
通过 Playwright 拦截 API 响应，保存 topics 数据为 JSON 文件
"""

import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Response

# 配置
GROUP_ID = "28888825825151"
TARGET_URL = f"https://wx.zsxq.com/group/{GROUP_ID}"
API_PATTERN = f"api.zsxq.com/v2/groups/{GROUP_ID}/topics"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "response"
USER_DATA_DIR = Path(__file__).parent / ".browser_data"

# 统计
captured_count = 0
running = True


def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_response(data: dict, url: str):
    """保存 API 响应为 JSON 文件"""
    global captured_count

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{GROUP_ID}_{timestamp}.json"
    filepath = OUTPUT_DIR / filename

    # 包装保存：包含原始 URL 和响应数据
    wrapper = {
        "captured_at": datetime.now().isoformat(),
        "url": url,
        "data": data
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)

    captured_count += 1
    topics_count = len(data.get("resp_data", {}).get("topics", []))
    print(f"[{captured_count}] 已保存: {filename} (topics: {topics_count})")


def handle_response(response: Response):
    """处理网络响应，匹配并保存 topics API 数据"""
    url = response.url

    # 匹配目标 API
    if API_PATTERN in url and "scope=all" in url:
        try:
            if response.status == 200:
                data = response.json()
                if "resp_data" in data and "topics" in data.get("resp_data", {}):
                    save_response(data, url)
        except Exception as e:
            print(f"解析响应失败: {e}")


def signal_handler(sig, frame):
    """处理 Ctrl+C 退出"""
    global running
    print(f"\n\n捕获到退出信号，共保存 {captured_count} 个响应文件")
    print(f"文件保存在: {OUTPUT_DIR.absolute()}")
    running = False
    sys.exit(0)


def main():
    ensure_output_dir()
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("知识星球 Topics 抓取工具")
    print("=" * 60)
    print(f"目标星球: {GROUP_ID}")
    print(f"输出目录: {OUTPUT_DIR.absolute()}")
    print("=" * 60)
    print("\n启动浏览器中...")

    with sync_playwright() as p:
        # 启动持久化浏览器（保存 cookies/localStorage，无需每次登录）
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 注册响应拦截
        page.on("response", handle_response)

        # 导航到目标页面
        print(f"\n正在打开: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        print("\n" + "=" * 60)
        print("请在浏览器中登录（如已登录则忽略）")
        print("登录后滚动页面以加载更多内容")
        print("按 Ctrl+C 退出并保存所有数据")
        print("=" * 60 + "\n")

        # 保持运行，等待用户交互
        try:
            while running:
                page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            pass
        finally:
            print(f"\n共保存 {captured_count} 个响应文件")
            print(f"文件保存在: {OUTPUT_DIR.absolute()}")
            context.close()


if __name__ == "__main__":
    main()
