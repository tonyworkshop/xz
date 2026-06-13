#!/usr/bin/env python3
"""
资源下载脚本
通过 Playwright 浏览器下载图片、文章等资源（需要登录态）
"""

import argparse
import logging
import random
import signal
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from db import get_connection

# 配置 logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# 目录配置
USER_DATA_DIR = Path(__file__).parent / ".browser_data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
ARTICLES_DIR = OUTPUT_DIR / "articles"
FILES_DIR = OUTPUT_DIR / "files"

# 全局状态
running = True


def ensure_output_dirs():
    """确保输出目录存在"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)


def get_pending_images(conn, limit: int = None):
    """获取未下载的图片"""
    sql = "SELECT * FROM images WHERE downloaded = 0 AND original_url IS NOT NULL"
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql).fetchall()


def get_pending_articles(conn, limit: int = None):
    """获取未下载的文章"""
    sql = "SELECT * FROM articles WHERE downloaded = 0 AND inline_article_url IS NOT NULL"
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql).fetchall()


def get_pending_files(conn, limit: int = None):
    """获取未下载的文件"""
    sql = "SELECT * FROM files WHERE downloaded = 0"
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql).fetchall()


def sanitize_filename(name: str) -> str:
    """替换文件系统保留字符，避免落盘失败"""
    if not name:
        return ""
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, "_")
    return name


def download_image(page, conn, image: dict) -> bool:
    """下载单张图片"""
    image_id = image["image_id"]
    url = image["original_url"]
    filename = image["filename"]

    logger.info(f"下载图片: {filename}")
    logger.debug(f"  URL: {url}")

    try:
        response = page.goto(url, wait_until="load", timeout=30000)

        if response and response.status == 200:
            content = response.body()
            local_path = IMAGES_DIR / filename
            local_path.write_bytes(content)

            conn.execute(
                "UPDATE images SET downloaded = 1, local_path = ? WHERE image_id = ?",
                (str(local_path.relative_to(OUTPUT_DIR)), image_id),
            )
            conn.commit()
            logger.info(f"  ✓ 已保存: {local_path} ({len(content)} bytes)")
            return True
        else:
            status = response.status if response else "无响应"
            logger.warning(f"  ✗ 下载失败: HTTP {status}")
            return False

    except Exception as e:
        logger.error(f"  ✗ 下载异常: {e}")
        return False


def download_article(page, conn, article: dict) -> bool:
    """下载单篇文章"""
    article_id = article["article_id"]
    url = article["inline_article_url"]
    filename = article["filename"]
    title = article["title"] or article_id

    logger.info(f"下载文章: {title}")
    logger.debug(f"  URL: {url}")

    try:
        response = page.goto(url, wait_until="networkidle", timeout=30000)

        if response and response.status == 200:
            html = page.content()
            local_path = ARTICLES_DIR / filename
            local_path.write_text(html, encoding="utf-8")

            conn.execute(
                "UPDATE articles SET downloaded = 1, local_path = ? WHERE article_id = ?",
                (str(local_path.relative_to(OUTPUT_DIR)), article_id),
            )
            conn.commit()
            logger.info(f"  ✓ 已保存: {local_path} ({len(html)} chars)")
            return True
        else:
            status = response.status if response else "无响应"
            logger.warning(f"  ✗ 下载失败: HTTP {status}")
            return False

    except Exception as e:
        logger.error(f"  ✗ 下载异常: {e}")
        return False


def download_file(page, conn, file: dict) -> bool:
    """下载单个文件（PDF / 音频等）"""
    file_id = file["file_id"]
    name = file["name"] or str(file_id)
    safe_name = sanitize_filename(name)
    filename = f"{file_id}_{safe_name}"

    logger.info(f"下载文件: {name}")

    try:
        # 第一步：在页面上下文中调 API 获取临时签名 URL
        api_url = f"https://api.zsxq.com/v2/files/{file_id}/download_url"
        logger.debug(f"  API: {api_url}")
        result = page.evaluate(
            """async (url) => {
                const r = await fetch(url, { credentials: 'include' });
                return await r.json();
            }""",
            api_url,
        )

        if not result or not result.get("succeeded"):
            logger.warning(f"  ✗ 获取下载 URL 失败: {result}")
            return False

        download_url = result.get("resp_data", {}).get("download_url")
        if not download_url:
            logger.warning(f"  ✗ 响应缺少 download_url: {result}")
            return False

        logger.debug(f"  URL: {download_url}")

        # 第二步：通过 APIRequestContext 下载二进制（避免触发浏览器的下载事件）
        # 文件可能较大，超时设为 60s
        response = page.context.request.get(download_url, timeout=60000)

        if response.ok:
            content = response.body()
            local_path = FILES_DIR / filename
            local_path.write_bytes(content)

            conn.execute(
                "UPDATE files SET downloaded = 1, local_path = ? WHERE file_id = ?",
                (str(local_path.relative_to(OUTPUT_DIR)), file_id),
            )
            conn.commit()
            logger.info(f"  ✓ 已保存: {local_path} ({len(content)} bytes)")
            return True
        else:
            logger.warning(f"  ✗ 下载失败: HTTP {response.status}")
            return False

    except Exception as e:
        logger.error(f"  ✗ 下载异常: {e}")
        return False


def random_delay(page, min_ms: int = 3000, max_ms: int = 5000):
    """随机延时"""
    delay = random.randint(min_ms, max_ms)
    logger.debug(f"延时 {delay}ms")
    page.wait_for_timeout(delay)


def signal_handler(sig, frame):
    """处理 Ctrl+C 退出"""
    global running
    print("\n\n捕获到退出信号，正在退出...")
    running = False
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="知识星球资源下载工具")
    parser.add_argument("--images", action="store_true", help="仅下载图片")
    parser.add_argument("--articles", action="store_true", help="仅下载文章")
    parser.add_argument("--files", action="store_true", help="仅下载文件")
    parser.add_argument("--limit", type=int, metavar="N", help="限制下载数量")
    parser.add_argument("--debug", action="store_true", help="启用 DEBUG 日志")
    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # 如果没有指定类型，则下载全部
    download_all = not (args.images or args.articles or args.files)

    ensure_output_dirs()
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("知识星球资源下载工具")
    print("=" * 60)

    conn = get_connection()

    # 统计待下载数量
    images = get_pending_images(conn, args.limit) if (download_all or args.images) else []
    articles = get_pending_articles(conn, args.limit) if (download_all or args.articles) else []
    files = get_pending_files(conn, args.limit) if (download_all or args.files) else []

    print(f"待下载图片: {len(images)}")
    print(f"待下载文章: {len(articles)}")
    print(f"待下载文件: {len(files)}")
    print("=" * 60)

    if not images and not articles and not files:
        print("没有待下载的资源")
        conn.close()
        return

    print("\n启动浏览器中...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            channel="chrome",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # 下载图片
        if images:
            print(f"\n开始下载图片 ({len(images)} 个)...")
            success_count = 0
            for i, image in enumerate(images, 1):
                if not running:
                    break
                print(f"\n[{i}/{len(images)}]", end=" ")
                if download_image(page, conn, dict(image)):
                    success_count += 1
                random_delay(page)
            print(f"\n图片下载完成: {success_count}/{len(images)}")

        # 下载文章
        if articles:
            print(f"\n开始下载文章 ({len(articles)} 个)...")
            success_count = 0
            for i, article in enumerate(articles, 1):
                if not running:
                    break
                print(f"\n[{i}/{len(articles)}]", end=" ")
                if download_article(page, conn, dict(article)):
                    success_count += 1
                random_delay(page)
            print(f"\n文章下载完成: {success_count}/{len(articles)}")

        # 下载文件
        if files:
            print(f"\n开始下载文件 ({len(files)} 个)...")
            # 导航到 zsxq 域以便后续 page.evaluate(fetch) 能带上 cookie 和签名头
            page.goto("https://wx.zsxq.com/", wait_until="load", timeout=30000)
            success_count = 0
            for i, file in enumerate(files, 1):
                if not running:
                    break
                print(f"\n[{i}/{len(files)}]", end=" ")
                if download_file(page, conn, dict(file)):
                    success_count += 1
                random_delay(page)
            print(f"\n文件下载完成: {success_count}/{len(files)}")

        context.close()

    conn.close()

    # 打印统计
    print("\n" + "=" * 60)
    print("下载完成！")
    print(f"图片目录: {IMAGES_DIR}")
    print(f"文章目录: {ARTICLES_DIR}")
    print(f"文件目录: {FILES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
