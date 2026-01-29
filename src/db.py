"""数据库操作模块"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "output" / "xz.db"

SCHEMA = """
-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    alias TEXT,
    avatar_url TEXT,
    location TEXT,
    updated_at TEXT
);

-- 2. 群组表
CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    background_url TEXT
);

-- 3. 专栏表
CREATE TABLE IF NOT EXISTS columns (
    column_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- 4. 帖子表
CREATE TABLE IF NOT EXISTS topics (
    topic_id INTEGER PRIMARY KEY,
    topic_uid TEXT,
    group_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    create_time TEXT,

    -- 通用字段
    title TEXT,
    annotation TEXT,
    digested INTEGER DEFAULT 0,
    silenced INTEGER DEFAULT 0,
    sticky INTEGER DEFAULT 0,

    -- 统计
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    readers_count INTEGER DEFAULT 0,
    reading_count INTEGER DEFAULT 0,
    rewards_count INTEGER DEFAULT 0,

    -- Q&A 类型
    question_user_id INTEGER,
    question_text TEXT,
    questionee_user_id INTEGER,
    question_fee INTEGER,
    question_expired INTEGER DEFAULT 0,
    question_anonymous INTEGER DEFAULT 0,
    answer_user_id INTEGER,
    answer_text TEXT,
    answered INTEGER DEFAULT 0,

    -- Talk 类型
    talk_user_id INTEGER,
    talk_text TEXT,

    -- 原始数据
    raw_json TEXT,

    FOREIGN KEY (group_id) REFERENCES groups(group_id)
);

-- 5. 帖子-专栏关联表
CREATE TABLE IF NOT EXISTS topic_columns (
    topic_id INTEGER NOT NULL,
    column_id INTEGER NOT NULL,
    PRIMARY KEY (topic_id, column_id),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id),
    FOREIGN KEY (column_id) REFERENCES columns(column_id)
);

-- 6. 评论表
CREATE TABLE IF NOT EXISTS comments (
    comment_id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    parent_comment_id INTEGER,
    user_id INTEGER NOT NULL,
    repliee_user_id INTEGER,
    create_time TEXT,
    text TEXT,
    likes_count INTEGER DEFAULT 0,
    rewards_count INTEGER DEFAULT 0,
    sticky INTEGER DEFAULT 0,
    group_owner_liked INTEGER DEFAULT 0,
    topic_owner_liked INTEGER DEFAULT 0,
    raw_json TEXT,

    FOREIGN KEY (topic_id) REFERENCES topics(topic_id),
    FOREIGN KEY (parent_comment_id) REFERENCES comments(comment_id)
);

-- 7. 图片资源表
CREATE TABLE IF NOT EXISTS images (
    image_id INTEGER PRIMARY KEY,
    topic_id INTEGER,
    comment_id INTEGER,
    image_type TEXT,
    filename TEXT,

    thumbnail_url TEXT,
    thumbnail_width INTEGER,
    thumbnail_height INTEGER,
    large_url TEXT,
    large_width INTEGER,
    large_height INTEGER,
    original_url TEXT,
    original_width INTEGER,
    original_height INTEGER,
    original_size INTEGER,

    -- 下载状态
    downloaded INTEGER DEFAULT 0,
    local_path TEXT,

    CHECK ((topic_id IS NOT NULL) OR (comment_id IS NOT NULL))
);

-- 8. 文件资源表（PDF、音频等）
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    name TEXT,
    hash TEXT,
    size INTEGER,
    duration INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    create_time TEXT,

    -- 下载状态
    downloaded INTEGER DEFAULT 0,
    local_path TEXT,

    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

-- 9. 文章资源表
CREATE TABLE IF NOT EXISTS articles (
    article_id TEXT PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    title TEXT,
    article_url TEXT,
    inline_article_url TEXT,
    filename TEXT,

    -- 下载状态
    downloaded INTEGER DEFAULT 0,
    local_path TEXT,

    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

-- 10. 点赞表
CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    create_time TEXT,

    FOREIGN KEY (topic_id) REFERENCES topics(topic_id),
    UNIQUE(topic_id, user_id)
);

-- 11. 打赏表
CREATE TABLE IF NOT EXISTS rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    create_time TEXT,

    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_topics_group ON topics(group_id);
CREATE INDEX IF NOT EXISTS idx_topics_type ON topics(type);
CREATE INDEX IF NOT EXISTS idx_topics_create_time ON topics(create_time);
CREATE INDEX IF NOT EXISTS idx_comments_topic ON comments(topic_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_images_topic ON images(topic_id);
CREATE INDEX IF NOT EXISTS idx_images_comment ON images(comment_id);
CREATE INDEX IF NOT EXISTS idx_images_downloaded ON images(downloaded);
CREATE INDEX IF NOT EXISTS idx_files_topic ON files(topic_id);
CREATE INDEX IF NOT EXISTS idx_files_downloaded ON files(downloaded);
CREATE INDEX IF NOT EXISTS idx_articles_downloaded ON articles(downloaded);
CREATE INDEX IF NOT EXISTS idx_likes_topic ON likes(topic_id);
CREATE INDEX IF NOT EXISTS idx_rewards_topic ON rewards(topic_id);
"""


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")


def upsert_user(conn: sqlite3.Connection, user: dict):
    """插入或更新用户"""
    if not user or "user_id" not in user:
        return
    conn.execute(
        """
        INSERT INTO users (user_id, name, alias, avatar_url, location, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            avatar_url = excluded.avatar_url,
            location = COALESCE(excluded.location, users.location),
            updated_at = datetime('now')
        """,
        (
            user["user_id"],
            user.get("name", ""),
            user.get("alias"),
            user.get("avatar_url"),
            user.get("location"),
        ),
    )


def upsert_group(conn: sqlite3.Connection, group: dict):
    """插入或更新群组"""
    if not group or "group_id" not in group:
        return
    conn.execute(
        """
        INSERT INTO groups (group_id, name, type, background_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(group_id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            background_url = excluded.background_url
        """,
        (
            group["group_id"],
            group.get("name", ""),
            group.get("type"),
            group.get("background_url"),
        ),
    )


def upsert_column(conn: sqlite3.Connection, column: dict):
    """插入或更新专栏"""
    if not column or "column_id" not in column:
        return
    conn.execute(
        """
        INSERT INTO columns (column_id, name)
        VALUES (?, ?)
        ON CONFLICT(column_id) DO UPDATE SET name = excluded.name
        """,
        (column["column_id"], column.get("name", "")),
    )


def upsert_topic(conn: sqlite3.Connection, topic: dict, raw_json: str = None):
    """插入或更新帖子"""
    topic_type = topic.get("type", "")

    # 提取 Q&A 字段
    question = topic.get("question", {})
    answer = topic.get("answer", {})
    question_owner = question.get("owner", {})
    questionee = question.get("questionee", {})
    answer_owner = answer.get("owner", {})
    question_fee_obj = question.get("fee", {})

    # 提取 Talk 字段
    talk = topic.get("talk", {})
    talk_owner = talk.get("owner", {})

    conn.execute(
        """
        INSERT INTO topics (
            topic_id, topic_uid, group_id, type, create_time,
            title, annotation, digested, silenced, sticky,
            likes_count, comments_count, readers_count, reading_count, rewards_count,
            question_user_id, question_text, questionee_user_id, question_fee,
            question_expired, question_anonymous, answer_user_id, answer_text, answered,
            talk_user_id, talk_text, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(topic_id) DO UPDATE SET
            topic_uid = excluded.topic_uid,
            type = excluded.type,
            create_time = COALESCE(excluded.create_time, topics.create_time),
            title = COALESCE(excluded.title, topics.title),
            annotation = COALESCE(excluded.annotation, topics.annotation),
            digested = excluded.digested,
            silenced = excluded.silenced,
            sticky = excluded.sticky,
            likes_count = excluded.likes_count,
            comments_count = excluded.comments_count,
            readers_count = excluded.readers_count,
            reading_count = excluded.reading_count,
            rewards_count = excluded.rewards_count,
            question_user_id = COALESCE(excluded.question_user_id, topics.question_user_id),
            question_text = COALESCE(excluded.question_text, topics.question_text),
            questionee_user_id = COALESCE(excluded.questionee_user_id, topics.questionee_user_id),
            question_fee = COALESCE(excluded.question_fee, topics.question_fee),
            question_expired = excluded.question_expired,
            question_anonymous = excluded.question_anonymous,
            answer_user_id = COALESCE(excluded.answer_user_id, topics.answer_user_id),
            answer_text = COALESCE(excluded.answer_text, topics.answer_text),
            answered = excluded.answered,
            talk_user_id = COALESCE(excluded.talk_user_id, topics.talk_user_id),
            talk_text = COALESCE(excluded.talk_text, topics.talk_text),
            raw_json = COALESCE(excluded.raw_json, topics.raw_json)
        """,
        (
            topic["topic_id"],
            topic.get("topic_uid"),
            topic["group"]["group_id"],
            topic_type,
            topic.get("create_time"),
            topic.get("title"),
            topic.get("annotation"),
            1 if topic.get("digested") else 0,
            1 if topic.get("silenced") else 0,
            1 if topic.get("sticky") else 0,
            topic.get("likes_count", 0),
            topic.get("comments_count", 0),
            topic.get("readers_count", 0),
            topic.get("reading_count", 0),
            topic.get("rewards_count", 0),
            question_owner.get("user_id") if topic_type == "q&a" else None,
            question.get("text") if topic_type == "q&a" else None,
            questionee.get("user_id") if topic_type == "q&a" else None,
            question_fee_obj.get("amount") if question_fee_obj else None,
            1 if question.get("expired") else 0,
            1 if question.get("anonymous") else 0,
            answer_owner.get("user_id") if topic_type == "q&a" else None,
            answer.get("text") if topic_type == "q&a" else None,
            1 if topic.get("answered") else 0,
            talk_owner.get("user_id") if topic_type == "talk" else None,
            talk.get("text") if topic_type == "talk" else None,
            raw_json,
        ),
    )


def upsert_comment(
    conn: sqlite3.Connection, comment: dict, topic_id: int, raw_json: str = None
):
    """插入或更新评论"""
    owner = comment.get("owner", {})
    repliee = comment.get("repliee", {})

    conn.execute(
        """
        INSERT INTO comments (
            comment_id, topic_id, parent_comment_id, user_id, repliee_user_id,
            create_time, text, likes_count, rewards_count, sticky,
            group_owner_liked, topic_owner_liked, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(comment_id) DO UPDATE SET
            topic_id = excluded.topic_id,
            parent_comment_id = COALESCE(excluded.parent_comment_id, comments.parent_comment_id),
            user_id = excluded.user_id,
            repliee_user_id = COALESCE(excluded.repliee_user_id, comments.repliee_user_id),
            create_time = COALESCE(excluded.create_time, comments.create_time),
            text = COALESCE(excluded.text, comments.text),
            likes_count = excluded.likes_count,
            rewards_count = excluded.rewards_count,
            sticky = excluded.sticky,
            group_owner_liked = excluded.group_owner_liked,
            topic_owner_liked = excluded.topic_owner_liked,
            raw_json = COALESCE(excluded.raw_json, comments.raw_json)
        """,
        (
            comment["comment_id"],
            topic_id,
            comment.get("parent_comment_id"),
            owner.get("user_id"),
            repliee.get("user_id"),
            comment.get("create_time"),
            comment.get("text"),
            comment.get("likes_count", 0),
            comment.get("rewards_count", 0),
            1 if comment.get("sticky") else 0,
            1 if comment.get("group_owner_liked") else 0,
            1 if comment.get("topic_owner_liked") else 0,
            raw_json,
        ),
    )


def upsert_image(
    conn: sqlite3.Connection, image: dict, topic_id: int = None, comment_id: int = None
):
    """插入或更新图片"""
    thumbnail = image.get("thumbnail", {})
    large = image.get("large", {})
    original = image.get("original", {})
    image_type = image.get("type", "jpg")

    conn.execute(
        """
        INSERT INTO images (
            image_id, topic_id, comment_id, image_type, filename,
            thumbnail_url, thumbnail_width, thumbnail_height,
            large_url, large_width, large_height,
            original_url, original_width, original_height, original_size
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(image_id) DO UPDATE SET
            topic_id = COALESCE(excluded.topic_id, images.topic_id),
            comment_id = COALESCE(excluded.comment_id, images.comment_id),
            image_type = excluded.image_type,
            filename = excluded.filename,
            thumbnail_url = excluded.thumbnail_url,
            thumbnail_width = excluded.thumbnail_width,
            thumbnail_height = excluded.thumbnail_height,
            large_url = excluded.large_url,
            large_width = excluded.large_width,
            large_height = excluded.large_height,
            original_url = excluded.original_url,
            original_width = excluded.original_width,
            original_height = excluded.original_height,
            original_size = COALESCE(excluded.original_size, images.original_size)
        """,
        (
            image["image_id"],
            topic_id,
            comment_id,
            image_type,
            f"{image['image_id']}.{image_type}",
            thumbnail.get("url"),
            thumbnail.get("width"),
            thumbnail.get("height"),
            large.get("url"),
            large.get("width"),
            large.get("height"),
            original.get("url"),
            original.get("width"),
            original.get("height"),
            original.get("size"),
        ),
    )


def upsert_file(conn: sqlite3.Connection, file: dict, topic_id: int):
    """插入或更新文件"""
    conn.execute(
        """
        INSERT INTO files (
            file_id, topic_id, name, hash, size, duration, download_count, create_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
            topic_id = excluded.topic_id,
            name = excluded.name,
            hash = excluded.hash,
            size = excluded.size,
            duration = excluded.duration,
            download_count = excluded.download_count,
            create_time = COALESCE(excluded.create_time, files.create_time)
        """,
        (
            file["file_id"],
            topic_id,
            file.get("name"),
            file.get("hash"),
            file.get("size"),
            file.get("duration", 0),
            file.get("download_count", 0),
            file.get("create_time"),
        ),
    )


def upsert_article(conn: sqlite3.Connection, article: dict, topic_id: int):
    """插入或更新文章"""
    article_id = article.get("article_id")
    if not article_id:
        return

    conn.execute(
        """
        INSERT INTO articles (
            article_id, topic_id, title, article_url, inline_article_url, filename
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
            topic_id = excluded.topic_id,
            title = COALESCE(excluded.title, articles.title),
            article_url = excluded.article_url,
            inline_article_url = excluded.inline_article_url,
            filename = excluded.filename
        """,
        (
            article_id,
            topic_id,
            article.get("title"),
            article.get("article_url"),
            article.get("inline_article_url"),
            f"{article_id}.html",
        ),
    )


def upsert_like(conn: sqlite3.Connection, like: dict, topic_id: int):
    """插入或更新点赞"""
    owner = like.get("owner", {})
    user_id = owner.get("user_id")
    if not user_id:
        return

    conn.execute(
        """
        INSERT INTO likes (topic_id, user_id, create_time)
        VALUES (?, ?, ?)
        ON CONFLICT(topic_id, user_id) DO UPDATE SET
            create_time = COALESCE(excluded.create_time, likes.create_time)
        """,
        (topic_id, user_id, like.get("create_time")),
    )


def upsert_topic_column(conn: sqlite3.Connection, topic_id: int, column_id: int):
    """插入帖子-专栏关联"""
    conn.execute(
        """
        INSERT OR IGNORE INTO topic_columns (topic_id, column_id)
        VALUES (?, ?)
        """,
        (topic_id, column_id),
    )


if __name__ == "__main__":
    init_db()
