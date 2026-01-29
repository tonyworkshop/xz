#!/usr/bin/env python3
"""
知识星球 Topics 抓取脚本
通过 Playwright 拦截 API 响应，保存 topics 数据为 JSON 文件
"""

import json
import logging
import random
import signal
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Response

# 配置 logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 配置
GROUP_ID = "28888825825151"
TARGET_URL = f"https://wx.zsxq.com/group/{GROUP_ID}"
TOPICS_API_PATTERN = f"api.zsxq.com/v2/groups/{GROUP_ID}/topics"
COMMENTS_API_PATTERN = "api.zsxq.com/v2/topics/"
TOPICS_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "json" / "topics"
COMMENTS_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "json" / "comments"
USER_DATA_DIR = Path(__file__).parent / ".browser_data"

# 统计
topics_captured_count = 0
comments_captured_count = 0
running = True

# 全局状态
pending_topics = []              # 待处理的 topic 队列，每项为 {topic_id, text}
processed_topic_ids = set()      # 已处理的 topic_id
comments_finished = False        # 当前 topic 评论是否加载完毕


def ensure_output_dirs():
    """确保输出目录存在"""
    TOPICS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMMENTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_topics_response(data: dict, url: str):
    """保存 topics API 响应为 JSON 文件"""
    global topics_captured_count

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{GROUP_ID}_{timestamp}.json"
    filepath = TOPICS_OUTPUT_DIR / filename

    wrapper = {
        "captured_at": datetime.now().isoformat(),
        "url": url,
        "data": data
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)

    topics_captured_count += 1
    topics_count = len(data.get("resp_data", {}).get("topics", []))
    print(f"[Topics #{topics_captured_count}] 已保存: {filename} (topics: {topics_count})")


def save_comments_response(data: dict, url: str, topic_id: str):
    """保存 comments API 响应为 JSON 文件"""
    global comments_captured_count

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{topic_id}_{timestamp}.json"
    filepath = COMMENTS_OUTPUT_DIR / filename

    wrapper = {
        "captured_at": datetime.now().isoformat(),
        "url": url,
        "topic_id": topic_id,
        "data": data
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)

    comments_captured_count += 1
    comments_count = len(data.get("resp_data", {}).get("comments", []))
    print(f"  [Comments #{comments_captured_count}] 已保存: {filename} (comments: {comments_count})")


def handle_response(response: Response):
    """处理网络响应，匹配并保存 topics API 数据"""
    global comments_finished
    url = response.url

    # 匹配 topics API
    if TOPICS_API_PATTERN in url and "scope=all" in url:
        try:
            if response.status == 200:
                data = response.json()
                if "resp_data" in data and "topics" in data.get("resp_data", {}):
                    save_topics_response(data, url)

                    # 将新 topic 加入待处理队列（保存 topic_id 和文本用于匹配）
                    pending_ids = {t["topic_id"] for t in pending_topics}
                    for topic in data.get("resp_data", {}).get("topics", []):
                        topic_id = str(topic.get("topic_id"))
                        if topic_id and topic_id not in processed_topic_ids and topic_id not in pending_ids:
                            # 提取帖子文本内容（用于在页面中定位）
                            text = (topic.get("talk", {}).get("text") or
                                    topic.get("question", {}).get("text") or
                                    topic.get("answer", {}).get("text") or "")
                            pending_topics.append({"topic_id": topic_id, "text": text[:50]})
        except Exception as e:
            print(f"解析 topics 响应失败: {e}")

    # 匹配 comments API
    elif COMMENTS_API_PATTERN in url and "/comments?" in url:
        try:
            if response.status == 200:
                data = response.json()
                if "resp_data" in data:
                    # 从 URL 提取 topic_id
                    # URL 格式: api.zsxq.com/v2/topics/{topic_id}/comments?...
                    path = urlparse(url).path
                    parts = path.split("/")
                    topic_id = None
                    for i, part in enumerate(parts):
                        if part == "topics" and i + 1 < len(parts):
                            topic_id = parts[i + 1]
                            break

                    if topic_id:
                        save_comments_response(data, url, topic_id)

                        # 检查是否加载完毕
                        comments = data.get("resp_data", {}).get("comments", [])
                        query = parse_qs(urlparse(url).query)
                        count = int(query.get("count", [30])[0])
                        comments_len = len(comments)

                        if comments_len == 0:
                            logger.debug(f"comments API: 返回 0 条评论，停止滚动")
                            comments_finished = True
                        elif comments_len < count:
                            logger.debug(f"comments API: 返回 {comments_len} 条 < 请求的 {count} 条，停止滚动")
                            comments_finished = True
                        else:
                            logger.debug(f"comments API: 返回 {comments_len} 条 = 请求的 {count} 条，继续滚动加载更多")
        except Exception as e:
            print(f"解析 comments 响应失败: {e}")


def find_topic_button(page, text_snippet: str):
    """在页面中查找包含指定文本的 app-topic，返回其"查看详情"按钮"""
    logger.debug(f"find_topic_button: 搜索文本 '{text_snippet[:30]}...'")
    if not text_snippet:
        logger.debug("find_topic_button: 文本为空，返回 None")
        return None

    # 查找包含该文本的 app-topic 元素索引
    match_index = page.evaluate('''(searchText) => {
        const topics = document.querySelectorAll('app-topic');
        for (let i = 0; i < topics.length; i++) {
            if (topics[i].textContent.includes(searchText)) return i;
        }
        return -1;
    }''', text_snippet)

    logger.debug(f"find_topic_button: 匹配结果 index={match_index}")
    if match_index == -1:
        return None

    # 获取该 app-topic 内的"查看详情"按钮
    button = page.evaluate_handle('''(idx) => {
        const topics = document.querySelectorAll('app-topic');
        return topics[idx]?.querySelector('div.details-container .text');
    }''', match_index)

    element = button.as_element()
    logger.debug(f"find_topic_button: 按钮元素 {'找到' if element else '未找到'}")
    return element


def click_detail_button(page, button):
    """点击按钮打开模态框"""
    logger.debug("click_detail_button: 开始点击按钮")
    try:
        logger.debug("click_detail_button: 滚动按钮到可见区域")
        button.scroll_into_view_if_needed()
        logger.debug("click_detail_button: 执行点击")
        button.click()
        logger.debug("click_detail_button: 等待模态框出现...")
        page.wait_for_selector('div.topic-detail', timeout=5000)
        logger.debug("click_detail_button: 模态框已出现")
        return True
    except Exception as e:
        logger.error(f"click_detail_button: 打开模态框失败 - {e}")
        return False


def scroll_modal_for_comments(page):
    """在模态框内滚动，触发 comments API 请求"""
    global comments_finished
    logger.debug("scroll_modal_for_comments: 开始滚动加载评论")

    max_scrolls = 50
    for scroll_count in range(max_scrolls):
        if comments_finished:
            logger.info(f"  评论加载完毕 (滚动 {scroll_count + 1} 次)")
            break
        logger.debug(f"scroll_modal_for_comments: 第 {scroll_count + 1} 次滚动")
        # 在模态框内滚动（不是 window）
        page.evaluate('''() => {
            const modal = document.querySelector('div.topic-detail');
            if (modal) modal.scrollTop = modal.scrollHeight;
        }''')
        page.wait_for_timeout(1500)


def close_modal(page):
    """关闭模态框"""
    logger.debug("close_modal: 开始关闭模态框")
    try:
        # 检查模态框是否存在并获取其位置
        modal = page.query_selector('div.topic-detail')
        if modal:
            box = modal.bounding_box()
            if box:
                logger.debug(f"close_modal: 模态框位置 x={box['x']:.0f}, y={box['y']:.0f}, w={box['width']:.0f}, h={box['height']:.0f}")
                # 点击模态框左侧外部的遮罩区域（绝对坐标）
                click_x = max(10, box['x'] - 50)  # 模态框左侧 50px，但至少是 10
                click_y = box['y'] + 100  # 模态框内偏上位置的高度
            else:
                logger.debug("close_modal: 无法获取模态框 bounding_box，使用默认点击位置")
                click_x, click_y = 10, 300
        else:
            logger.debug("close_modal: 未找到模态框元素")
            return True  # 模态框不存在，视为已关闭

        # 点击遮罩区域关闭（使用绝对坐标）
        logger.debug(f"close_modal: 点击绝对坐标 ({click_x:.0f}, {click_y:.0f})")
        page.mouse.click(click_x, click_y)

        logger.debug("close_modal: 等待模态框消失...")
        page.wait_for_selector('div.topic-detail', state='detached', timeout=3000)
        logger.debug("close_modal: 模态框已关闭")
        return True
    except Exception as e:
        logger.error(f"close_modal: 关闭失败 - {e}")
        return False


def process_pending_comments(page):
    """处理待处理队列中的所有 topic（通过点击模态框方式）"""
    global comments_finished

    batch = list(pending_topics)  # 复制当前批次
    pending_topics.clear()
    logger.debug(f"process_pending_comments: 处理 {len(batch)} 个待处理 topics")

    for i, topic_info in enumerate(batch):
        topic_id = topic_info["topic_id"]
        text_snippet = topic_info["text"]

        if topic_id in processed_topic_ids:
            logger.debug(f"process_pending_comments: topic_id={topic_id} 已处理，跳过")
            continue

        comments_finished = False
        logger.info(f"\n→ 抓取评论: topic_id={topic_id} ({i+1}/{len(batch)})")

        # 通过文本匹配找到帖子的"查看详情"按钮
        button = find_topic_button(page, text_snippet)
        if not button:
            logger.warning(f"  未找到帖子按钮，跳过 (text: {text_snippet[:20]}...)")
            processed_topic_ids.add(topic_id)
            continue

        # 点击打开模态框
        if not click_detail_button(page, button):
            processed_topic_ids.add(topic_id)
            continue

        logger.debug("process_pending_comments: 等待初始评论加载...")
        page.wait_for_timeout(1500)  # 等待初始评论加载

        # 在模态框内滚动加载评论
        scroll_modal_for_comments(page)

        # 关闭模态框
        logger.debug("process_pending_comments: 关闭模态框")
        if not close_modal(page):
            logger.warning(f"  关闭模态框失败，尝试按 Escape")
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        processed_topic_ids.add(topic_id)
        logger.debug(f"process_pending_comments: topic_id={topic_id} 处理完成")

        # 随机延时 (topic 间隔 5-8 秒)
        delay = random.randint(5000, 8000)
        logger.debug(f"process_pending_comments: 随机延时 {delay}ms")
        page.wait_for_timeout(delay)


def auto_fetch_all(page):
    """自动抓取所有 topics 和 comments"""
    print("\n" + "=" * 60)
    print("开始自动抓取...")
    print("=" * 60)

    no_new_topics_count = 0
    max_no_new_attempts = 5  # 连续 5 次没有新 topics 则认为到底

    while True:
        # 记录当前状态
        prev_pending = len(pending_topics)
        prev_processed = len(processed_topic_ids)

        # 滚动加载一批 topics
        print(f"\n滚动加载 topics... (已处理: {prev_processed}, 待处理: {prev_pending})")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)

        # 检查是否有新 topics
        new_count = len(pending_topics) - prev_pending
        if new_count > 0:
            print(f"新增 {new_count} 个 topics")
            no_new_topics_count = 0

            # 处理这批 topics 的评论
            if len(pending_topics) > 0:
                process_pending_comments(page)
        else:
            no_new_topics_count += 1
            print(f"无新增 topics ({no_new_topics_count}/{max_no_new_attempts})")

            # 连续多次无新内容，认为已到底
            if no_new_topics_count >= max_no_new_attempts:
                # 最后处理剩余的待处理 topics
                if len(pending_topics) > 0:
                    process_pending_comments(page)
                break

        # 随机延时
        delay = random.randint(1000, 2000)
        page.wait_for_timeout(delay)

    print("\n" + "=" * 60)
    print(f"自动抓取完成！")
    print(f"共处理 {len(processed_topic_ids)} 个 topics")
    print(f"Topics 文件: {topics_captured_count} 个")
    print(f"Comments 文件: {comments_captured_count} 个")
    print("=" * 60)


def signal_handler(sig, frame):
    """处理 Ctrl+C 退出"""
    global running
    print(f"\n\n捕获到退出信号")
    print(f"Topics 文件: {topics_captured_count} 个 -> {TOPICS_OUTPUT_DIR.absolute()}")
    print(f"Comments 文件: {comments_captured_count} 个 -> {COMMENTS_OUTPUT_DIR.absolute()}")
    print(f"已处理 topics: {len(processed_topic_ids)} 个")
    running = False
    sys.exit(0)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="知识星球 Topics & Comments 抓取工具")
    parser.add_argument("--auto", action="store_true", help="自动模式：自动滚动抓取所有内容")
    parser.add_argument("--wait-login", type=int, default=0, help="等待登录的秒数（自动模式下使用）")
    parser.add_argument("--open", action="store_true", help="仅打开浏览器，不做任何操作")
    parser.add_argument("--debug", action="store_true", help="启用 DEBUG 日志（详细）")
    parser.add_argument("--info", action="store_true", help="启用 INFO 日志（默认）")
    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("日志级别: DEBUG")
    else:
        logger.setLevel(logging.INFO)

    ensure_output_dirs()
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("知识星球 Topics & Comments 抓取工具")
    print("=" * 60)
    print(f"目标星球: {GROUP_ID}")
    if not args.open:
        print(f"Topics 输出: {TOPICS_OUTPUT_DIR.absolute()}")
        print(f"Comments 输出: {COMMENTS_OUTPUT_DIR.absolute()}")
    mode_str = "仅打开" if args.open else ("自动" if args.auto else "手动")
    print(f"模式: {mode_str}")
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

        # 导航到目标页面
        print(f"\n正在打开: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        if args.open:
            # 仅打开模式：不注册响应拦截
            print("\n" + "=" * 60)
            print("仅打开浏览器模式")
            print("可手动登录或检查页面状态")
            print("按 Ctrl+C 退出")
            print("=" * 60 + "\n")

            try:
                while running:
                    page.wait_for_timeout(1000)
            except KeyboardInterrupt:
                pass
        else:
            # 注册响应拦截（正常模式）
            page.on("response", handle_response)

            if args.auto:
                # 自动模式
                logger.warning("=" * 50)
                logger.warning("【自动模式】将自动滚动并抓取所有 topics 和 comments")
                logger.warning("=" * 50)
                if args.wait_login > 0:
                    print(f"\n等待 {args.wait_login} 秒进行登录...")
                    page.wait_for_timeout(args.wait_login * 1000)

                auto_fetch_all(page)
            else:
                # 手动模式
                logger.warning("=" * 50)
                logger.warning("【手动模式】仅拦截保存网络请求，不会自动抓取评论")
                logger.warning("如需自动抓取，请使用: --auto 参数")
                logger.warning("=" * 50)
                print("\n" + "=" * 60)
                print("请在浏览器中登录（如已登录则忽略）")
                print("登录后滚动页面以加载更多内容")
                print("按 Ctrl+C 退出并保存所有数据")
                print("=" * 60 + "\n")

                try:
                    while running:
                        page.wait_for_timeout(1000)
                except KeyboardInterrupt:
                    pass

            print(f"\n" + "=" * 60)
            print(f"Topics 文件: {topics_captured_count} 个 -> {TOPICS_OUTPUT_DIR.absolute()}")
            print(f"Comments 文件: {comments_captured_count} 个 -> {COMMENTS_OUTPUT_DIR.absolute()}")
            print(f"已处理 topics: {len(processed_topic_ids)} 个")
            print("=" * 60)

        context.close()


if __name__ == "__main__":
    main()
