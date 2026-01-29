"""JSON 数据导入脚本"""
import json
from pathlib import Path

from db import (
    get_connection,
    init_db,
    upsert_article,
    upsert_column,
    upsert_comment,
    upsert_file,
    upsert_group,
    upsert_image,
    upsert_like,
    upsert_topic,
    upsert_topic_column,
    upsert_user,
)

TOPICS_DIR = Path(__file__).parent.parent / "output" / "topics"
COMMENTS_DIR = Path(__file__).parent.parent / "output" / "comments"


def extract_users_from_topic(topic: dict) -> list[dict]:
    """从帖子中提取所有用户"""
    users = []

    # Q&A 类型
    question = topic.get("question", {})
    if question.get("owner"):
        users.append(question["owner"])
    if question.get("questionee"):
        users.append(question["questionee"])

    answer = topic.get("answer", {})
    if answer.get("owner"):
        users.append(answer["owner"])

    # Talk 类型
    talk = topic.get("talk", {})
    if talk.get("owner"):
        users.append(talk["owner"])

    # 点赞用户
    for like in topic.get("latest_likes", []):
        if like.get("owner"):
            users.append(like["owner"])

    # 展示评论中的用户
    for comment in topic.get("show_comments", []):
        if comment.get("owner"):
            users.append(comment["owner"])
        if comment.get("repliee"):
            users.append(comment["repliee"])

    return users


def extract_users_from_comment(comment: dict) -> list[dict]:
    """从评论中提取所有用户"""
    users = []
    if comment.get("owner"):
        users.append(comment["owner"])
    if comment.get("repliee"):
        users.append(comment["repliee"])
    return users


def import_topic(conn, topic: dict):
    """导入单个帖子及其关联数据"""
    topic_id = topic["topic_id"]

    # 1. 导入群组
    upsert_group(conn, topic.get("group", {}))

    # 2. 导入用户
    for user in extract_users_from_topic(topic):
        upsert_user(conn, user)

    # 3. 导入帖子
    upsert_topic(conn, topic, json.dumps(topic, ensure_ascii=False))

    # 4. 导入专栏和关联
    for column in topic.get("columns", []):
        upsert_column(conn, column)
        upsert_topic_column(conn, topic_id, column["column_id"])

    # 5. 导入图片
    # Q&A 问题图片
    question = topic.get("question", {})
    for image in question.get("images", []):
        upsert_image(conn, image, topic_id=topic_id)

    # Talk 图片
    talk = topic.get("talk", {})
    for image in talk.get("images", []):
        upsert_image(conn, image, topic_id=topic_id)

    # 6. 导入文件
    for file in talk.get("files", []):
        upsert_file(conn, file, topic_id)

    # 7. 导入文章
    article = talk.get("article")
    if article:
        upsert_article(conn, article, topic_id)

    # 8. 导入点赞
    for like in topic.get("latest_likes", []):
        upsert_like(conn, like, topic_id)
        # 同时导入点赞用户
        if like.get("owner"):
            upsert_user(conn, like["owner"])

    # 9. 导入展示评论
    for comment in topic.get("show_comments", []):
        import_comment(conn, comment, topic_id)


def import_comment(conn, comment: dict, topic_id: int):
    """导入单个评论及其关联数据"""
    # 1. 导入用户
    for user in extract_users_from_comment(comment):
        upsert_user(conn, user)

    # 2. 导入评论
    upsert_comment(conn, comment, topic_id, json.dumps(comment, ensure_ascii=False))

    # 3. 导入评论图片
    for image in comment.get("images", []):
        upsert_image(conn, image, comment_id=comment["comment_id"])


def import_topics_file(conn, file_path: Path):
    """导入单个 topics JSON 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resp_data = data.get("data", {}).get("resp_data", {})
    topics = resp_data.get("topics", [])

    for topic in topics:
        import_topic(conn, topic)

    return len(topics)


def import_comments_file(conn, file_path: Path):
    """导入单个 comments JSON 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    topic_id_str = data.get("topic_id")
    if not topic_id_str:
        return 0

    topic_id = int(topic_id_str)
    resp_data = data.get("data", {}).get("resp_data", {})
    comments = resp_data.get("comments", [])

    # 也处理 replied_comments（被回复的评论）
    replied_comments = resp_data.get("replied_comments", [])

    count = 0
    for comment in comments:
        import_comment(conn, comment, topic_id)
        count += 1

    for comment in replied_comments:
        import_comment(conn, comment, topic_id)
        count += 1

    return count


def import_all():
    """导入所有数据"""
    # 初始化数据库
    init_db()

    conn = get_connection()

    # 导入 topics
    topics_files = sorted(TOPICS_DIR.glob("*.json"))
    total_topics = 0
    print(f"发现 {len(topics_files)} 个 topics 文件")

    for i, file_path in enumerate(topics_files, 1):
        count = import_topics_file(conn, file_path)
        total_topics += count
        if i % 10 == 0 or i == len(topics_files):
            print(f"  处理 topics 文件: {i}/{len(topics_files)}")
            conn.commit()

    conn.commit()
    print(f"导入 topics 完成: {total_topics} 条")

    # 导入 comments
    comments_files = sorted(COMMENTS_DIR.glob("*.json"))
    total_comments = 0
    print(f"发现 {len(comments_files)} 个 comments 文件")

    for i, file_path in enumerate(comments_files, 1):
        count = import_comments_file(conn, file_path)
        total_comments += count
        if i % 50 == 0 or i == len(comments_files):
            print(f"  处理 comments 文件: {i}/{len(comments_files)}")
            conn.commit()

    conn.commit()
    print(f"导入 comments 完成: {total_comments} 条")

    # 输出统计
    print("\n=== 导入统计 ===")
    stats = [
        ("topics", "帖子"),
        ("comments", "评论"),
        ("users", "用户"),
        ("groups", "群组"),
        ("images", "图片"),
        ("files", "文件"),
        ("articles", "文章"),
        ("likes", "点赞"),
    ]

    for table, name in stats:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {name}: {count}")

    # 资源下载统计
    print("\n=== 资源下载状态 ===")
    for table, name in [("images", "图片"), ("files", "文件"), ("articles", "文章")]:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        downloaded = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE downloaded = 1"
        ).fetchone()[0]
        print(f"  {name}: {downloaded}/{total} 已下载")

    conn.close()


if __name__ == "__main__":
    import_all()
