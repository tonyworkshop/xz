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
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import glob

from playwright.sync_api import sync_playwright, Response

# 配置 logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def load_config() -> dict:
    """读取配置文件"""
    config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


# 配置
CONFIG = load_config()
GROUP_ID = CONFIG["group_id"]
TARGET_URL = f"https://wx.zsxq.com/group/{GROUP_ID}"
TOPICS_API_PATTERN = f"api.zsxq.com/v2/groups/{GROUP_ID}/topics"
COMMENTS_API_PATTERN = "api.zsxq.com/v2/topics/"
TOPICS_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "topics"
COMMENTS_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "comments"
CLICK_CACHE_PATH = Path(__file__).parent.parent / "output" / "click_detail.json"
UPDATE_CACHE_PATH = Path(__file__).parent.parent / "output" / "update_click_detail.json"
ERROR_FILE_PATH = Path(__file__).parent.parent / "output" / "last_error.txt"
USER_DATA_DIR = Path(__file__).parent / ".browser_data"

# 统计
topics_captured_count = 0
comments_captured_count = 0
running = True

# 全局状态
comments_finished = False        # 当前 topic 评论是否加载完毕
current_topic_page_id = 0        # 当前 topic 的评论页码（每个 topic 独立计数）


def ensure_output_dirs():
    """确保输出目录存在"""
    TOPICS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMMENTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_click_cache() -> dict:
    """加载点击缓存"""
    if CLICK_CACHE_PATH.exists():
        try:
            with open(CLICK_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载点击缓存失败: {e}")
    return {}


def save_click_cache(cache: dict, cache_path: Path = CLICK_CACHE_PATH):
    """保存点击缓存到磁盘"""
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存点击缓存失败: {e}")


def get_all_topic_keys(page) -> list:
    """
    获取页面所有 app-topic 的 key 信息
    返回: [{index, key, hasContent, contentType, outerHTMLSnippet}, ...]
    """
    return page.evaluate('''() => {
        function djb2Hash(str) {
            let hash = 5381;
            for (let i = 0; i < str.length; i++) {
                hash = ((hash << 5) + hash) + str.charCodeAt(i);
            }
            return (hash >>> 0).toString(16);
        }

        const topics = document.querySelectorAll('app-topic');
        return Array.from(topics).map((topic, index) => {
            const answerContent = topic.querySelector('app-answer-content');
            const talkContent = topic.querySelector('app-talk-content');
            const content = answerContent || talkContent;
            const contentType = answerContent ? 'answer' : (talkContent ? 'talk' : null);

            return {
                index: index,
                key: content ? djb2Hash(content.outerHTML) : null,
                hasContent: !!content,
                contentType: contentType,
                outerHTMLSnippet: topic.outerHTML.substring(0, 200)
            };
        });
    }''')


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


def comments_file_exists(topic_id: str) -> bool:
    """检查 topic 的 comments 文件是否已存在（匹配 {topic_id}_*.json）"""
    pattern = str(COMMENTS_OUTPUT_DIR / f"{topic_id}_*.json")
    return len(glob.glob(pattern)) > 0


def save_comments_response(data: dict, url: str, topic_id: str):
    """保存 comments API 响应为 JSON 文件（每页单独保存）"""
    global comments_captured_count, current_topic_page_id

    filename = f"{topic_id}_{current_topic_page_id}.json"
    filepath = COMMENTS_OUTPUT_DIR / filename

    wrapper = {
        "captured_at": datetime.now().isoformat(),
        "url": url,
        "topic_id": topic_id,
        "page_id": current_topic_page_id,
        "data": data
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)

    comments_captured_count += 1
    current_topic_page_id += 1
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


def get_topic_details_button(page, topic_index: int):
    """获取指定索引的 app-topic 的"查看详情"按钮"""
    logger.debug(f"get_topic_details_button: 获取 index={topic_index} 的按钮")

    button = page.evaluate_handle('''(idx) => {
        const topics = document.querySelectorAll('app-topic');
        return topics[idx]?.querySelector('div.details-container .text');
    }''', topic_index)

    element = button.as_element()
    logger.debug(f"get_topic_details_button: 按钮元素 {'找到' if element else '未找到'}")
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


def process_all_topics_on_page(page, click_cache: dict, cache_path: Path = CLICK_CACHE_PATH, max_clicks: int = None) -> tuple:
    """
    处理当前页面上所有 app-topic 元素
    返回: (clicked_count, reached_limit)
        - clicked_count: 本次处理（点击）的 topic 数量
        - reached_limit: 是否达到 max_clicks 限制
    """
    global comments_finished, current_topic_page_id

    # 获取页面所有 topic 的 key 信息
    topic_infos = get_all_topic_keys(page)
    logger.info(f"页面上共有 {len(topic_infos)} 个 app-topic 元素")

    clicked_count = 0

    for info in topic_infos:
        # 检查是否达到点击限制
        if max_clicks is not None and clicked_count >= max_clicks:
            logger.info(f"已达到点击限制 ({max_clicks})，停止处理")
            return clicked_count, True

        index = info["index"]
        key = info["key"]
        has_content = info["hasContent"]
        content_type = info["contentType"]
        html_snippet = info["outerHTMLSnippet"]

        # 检查是否有 content 元素
        if not has_content or not key:
            logger.warning(f"app-topic index={index} 没有 content 元素，跳过")
            logger.warning(f"  contentType: {content_type}")
            logger.warning(f"  outerHTML 片段: {html_snippet}")
            # 记录错误到文件，供通知使用
            with open(ERROR_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] unknown topic type at index={index}\n")
                f.write(f"  contentType: {content_type}\n")
                f.write(f"  outerHTML: {html_snippet}\n\n")
            continue

        # 检查是否已点击过
        if key in click_cache:
            logger.debug(f"topic index={index} key={key[:8]}... 已点击过，跳过")
            continue

        logger.info(f"\n→ 处理 topic: index={index}, key={key[:8]}..., type={content_type}")

        # 获取"查看详情"按钮
        button = get_topic_details_button(page, index)
        if not button:
            logger.warning(f"  未找到查看详情按钮，标记为已处理并跳过")
            click_cache[key] = datetime.now().isoformat()
            save_click_cache(click_cache, cache_path)
            continue

        # 重置评论状态
        current_topic_page_id = 0
        comments_finished = False

        # 点击打开模态框
        if not click_detail_button(page, button):
            logger.warning(f"  打开模态框失败，标记为已处理并跳过")
            click_cache[key] = datetime.now().isoformat()
            save_click_cache(click_cache, cache_path)
            continue

        logger.debug("等待初始评论加载...")
        page.wait_for_timeout(1500)

        # 在模态框内滚动加载评论
        scroll_modal_for_comments(page)

        # 关闭模态框
        logger.debug("关闭模态框")
        if not close_modal(page):
            logger.warning(f"  关闭模态框失败，尝试按 Escape")
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # 标记为已点击并立即保存
        click_cache[key] = datetime.now().isoformat()
        save_click_cache(click_cache, cache_path)
        clicked_count += 1
        logger.info(f"  ✓ 已处理并保存 (累计点击: {clicked_count})")

        # 随机延时 (topic 间隔 5-8 秒)
        delay = random.randint(5000, 8000)
        logger.debug(f"随机延时 {delay}ms")
        page.wait_for_timeout(delay)

    return clicked_count, False


def auto_fetch_all(page):
    """自动抓取所有 topics 和 comments"""
    print("\n" + "=" * 60)
    print("开始自动抓取...")
    print("=" * 60)

    # 加载点击缓存
    click_cache = load_click_cache()
    print(f"已加载点击缓存: {len(click_cache)} 个已处理 topics")

    total_clicked = 0
    no_new_click_count = 0
    max_no_new_attempts = 5  # 连续 5 次没有新点击则认为到底

    while True:
        # 处理当前页面上的所有 topics
        print(f"\n处理当前页面 topics... (缓存中已有: {len(click_cache)})")
        clicked, _ = process_all_topics_on_page(page, click_cache)
        total_clicked += clicked

        if clicked > 0:
            print(f"本轮点击了 {clicked} 个 topics")
            no_new_click_count = 0
        else:
            no_new_click_count += 1
            print(f"本轮无新点击 ({no_new_click_count}/{max_no_new_attempts})")

        # 连续多次无新点击，认为已处理完当前可见内容
        if no_new_click_count >= max_no_new_attempts:
            break

        # 滚动加载更多 topics
        print("滚动加载更多内容...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)

        # 随机延时
        delay = random.randint(1000, 2000)
        page.wait_for_timeout(delay)

    print("\n" + "=" * 60)
    print(f"自动抓取完成！")
    print(f"本次点击: {total_clicked} 个 topics")
    print(f"缓存中共有: {len(click_cache)} 个已处理 topics")
    print(f"Topics 文件: {topics_captured_count} 个")
    print(f"Comments 文件: {comments_captured_count} 个")
    print("=" * 60)


def update_fetch(page, max_clicks: int):
    """更新模式：抓取最新 N 个 topics 的评论"""
    print("\n" + "=" * 60)
    print(f"开始更新抓取 (最多 {max_clicks} 个 topics)...")
    print("=" * 60)

    # 删除旧的 update cache
    if UPDATE_CACHE_PATH.exists():
        UPDATE_CACHE_PATH.unlink()
        logger.info(f"已删除旧的 update cache: {UPDATE_CACHE_PATH}")

    # 使用空 cache 开始
    click_cache = {}
    total_clicked = 0

    while total_clicked < max_clicks:
        print(f"\n处理当前页面 topics... (已点击: {total_clicked}/{max_clicks})")
        clicked, reached_limit = process_all_topics_on_page(
            page, click_cache,
            cache_path=UPDATE_CACHE_PATH,
            max_clicks=max_clicks - total_clicked
        )
        total_clicked += clicked

        if reached_limit:
            logger.info("已达到点击限制")
            break

        if clicked == 0:
            # 没有新的可点击内容，滚动加载更多
            print("滚动加载更多内容...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2500)

            # 再次检查是否有新内容
            clicked, reached_limit = process_all_topics_on_page(
                page, click_cache,
                cache_path=UPDATE_CACHE_PATH,
                max_clicks=max_clicks - total_clicked
            )
            total_clicked += clicked

            if clicked == 0 or reached_limit:
                break

    print("\n" + "=" * 60)
    print(f"更新抓取完成！")
    print(f"本次点击: {total_clicked} 个 topics")
    print(f"Topics 文件: {topics_captured_count} 个")
    print(f"Comments 文件: {comments_captured_count} 个")
    print("=" * 60)


def manual_fetch(page):
    """手动模式：仅拦截保存，用户自己滚动"""
    print("\n" + "=" * 60)
    print("手动模式：仅拦截保存网络请求")
    print("请在浏览器中登录（如已登录则忽略）")
    print("登录后滚动页面以加载更多内容")
    print("按 Ctrl+C 退出并保存所有数据")
    print("=" * 60 + "\n")

    try:
        while running:
            page.wait_for_timeout(1000)
    except KeyboardInterrupt:
        pass


def manual_fetch_with_limit(page, max_topics: int):
    """手动模式 + N 限制：监听点击事件，达到 N 个后提示并退出"""
    global comments_finished, current_topic_page_id

    print("\n" + "=" * 60)
    print(f"手动模式：抓取 {max_topics} 个 topics 后自动停止")
    print("请在浏览器中手动点击 '查看详情' 打开评论")
    print("按 Ctrl+C 提前退出")
    print("=" * 60 + "\n")

    # 使用空 cache 开始（每次都是新的计数）
    click_cache = {}
    total_clicked = 0

    try:
        while running and total_clicked < max_topics:
            # 获取页面所有 topic 的 key 信息
            topic_infos = get_all_topic_keys(page)

            # 检查是否有新的已点击 topic（通过检测 cache 外的 topic）
            for info in topic_infos:
                key = info["key"]
                if key and key not in click_cache:
                    # 检查这个 topic 是否已经有模态框打开（用户手动点击了）
                    modal = page.query_selector('div.topic-detail')
                    if modal:
                        logger.info(f"\n→ 检测到手动点击 topic: key={key[:8]}...")

                        # 重置评论状态
                        current_topic_page_id = 0
                        comments_finished = False

                        # 等待用户滚动加载评论
                        logger.info("  等待用户滚动加载评论...")
                        while not comments_finished:
                            page.wait_for_timeout(1000)
                            # 检查模态框是否还存在
                            if not page.query_selector('div.topic-detail'):
                                break

                        # 标记为已点击
                        click_cache[key] = datetime.now().isoformat()
                        total_clicked += 1
                        logger.info(f"  ✓ 已处理 ({total_clicked}/{max_topics})")

                        if total_clicked >= max_topics:
                            break

            page.wait_for_timeout(500)

    except KeyboardInterrupt:
        pass

    print("\n" + "=" * 60)
    print(f"手动抓取完成！")
    print(f"本次处理: {total_clicked} 个 topics")
    print(f"Topics 文件: {topics_captured_count} 个")
    print(f"Comments 文件: {comments_captured_count} 个")
    print("=" * 60)


def signal_handler(sig, frame):
    """处理 Ctrl+C 退出"""
    global running
    print(f"\n\n捕获到退出信号")
    print(f"Topics 文件: {topics_captured_count} 个 -> {TOPICS_OUTPUT_DIR.absolute()}")
    print(f"Comments 文件: {comments_captured_count} 个 -> {COMMENTS_OUTPUT_DIR.absolute()}")
    running = False
    sys.exit(0)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="知识星球 Topics & Comments 抓取工具")
    parser.add_argument("--manual", action="store_true", help="手动模式：仅拦截保存，不自动滚动")
    parser.add_argument("--update", type=int, metavar="N", help="抓取最新 N 个 topics 的评论")
    parser.add_argument("--wait-login", type=int, default=0, help="等待登录的秒数")
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
    if ERROR_FILE_PATH.exists():
        ERROR_FILE_PATH.unlink()
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("知识星球 Topics & Comments 抓取工具")
    print("=" * 60)
    print(f"目标星球: {GROUP_ID}")
    if not args.open:
        print(f"Topics 输出: {TOPICS_OUTPUT_DIR.absolute()}")
        print(f"Comments 输出: {COMMENTS_OUTPUT_DIR.absolute()}")
    if args.open:
        mode_str = "仅打开"
    elif args.manual:
        mode_str = "手动" + (f"(限{args.update}个)" if args.update else "")
    elif args.update:
        mode_str = f"更新({args.update}个)"
    else:
        mode_str = "全量"
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

            # 等待登录（如果指定）
            if args.wait_login > 0:
                print(f"\n等待 {args.wait_login} 秒进行登录...")
                page.wait_for_timeout(args.wait_login * 1000)

            if args.update:
                if args.manual:
                    # 手动模式 + N 限制
                    logger.warning("=" * 50)
                    logger.warning(f"【手动模式】抓取 {args.update} 个后自动停止")
                    logger.warning("=" * 50)
                    manual_fetch_with_limit(page, args.update)
                else:
                    # 自动更新模式
                    logger.warning("=" * 50)
                    logger.warning(f"【更新模式】将抓取最新 {args.update} 个 topics 的评论")
                    logger.warning("=" * 50)
                    update_fetch(page, args.update)
            elif args.manual:
                # 纯手动模式
                logger.warning("=" * 50)
                logger.warning("【手动模式】仅拦截保存网络请求，不会自动抓取评论")
                logger.warning("=" * 50)
                manual_fetch(page)
            else:
                # 默认：自动全量抓取
                logger.warning("=" * 50)
                logger.warning("【全量模式】将自动滚动并抓取所有 topics 和 comments")
                logger.warning("=" * 50)
                auto_fetch_all(page)

            print(f"\n" + "=" * 60)
            print(f"Topics 文件: {topics_captured_count} 个 -> {TOPICS_OUTPUT_DIR.absolute()}")
            print(f"Comments 文件: {comments_captured_count} 个 -> {COMMENTS_OUTPUT_DIR.absolute()}")
            print("=" * 60)

        context.close()


if __name__ == "__main__":
    main()
