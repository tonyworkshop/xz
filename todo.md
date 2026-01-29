# 资源下载实现方案

## 第一阶段：Images 和 Articles

### 1. 创建 download_resources.py

```python
# 核心流程
1. 从数据库查询 downloaded = 0 的资源
2. 启动 Playwright 持久化浏览器（复用登录态）
3. 遍历资源，逐个下载
4. 更新数据库状态
```

### 2. 下载 Images

```python
def download_image(page, conn, image):
    url = image["original_url"]
    response = page.goto(url)

    if response.status == 200:
        content = response.body()
        local_path = IMAGES_DIR / image["filename"]
        local_path.write_bytes(content)

        conn.execute(
            "UPDATE images SET downloaded = 1, local_path = ? WHERE image_id = ?",
            (str(local_path), image["image_id"])
        )
        conn.commit()
```

### 3. 下载 Articles

```python
def download_article(page, conn, article):
    url = article["inline_article_url"]
    page.goto(url, wait_until="networkidle")

    html = page.content()
    local_path = ARTICLES_DIR / article["filename"]
    local_path.write_text(html, encoding="utf-8")

    conn.execute(
        "UPDATE articles SET downloaded = 1, local_path = ? WHERE article_id = ?",
        (str(local_path), article["article_id"])
    )
    conn.commit()
```

### 4. 命令行参数

```bash
uv run python src/download_resources.py           # 下载全部
uv run python src/download_resources.py --images  # 仅图片
uv run python src/download_resources.py --articles # 仅文章
uv run python src/download_resources.py --limit 10 # 限制数量
```

---

## 第二阶段：Files（待抓包确认）

需要通过 MCP 浏览器打开知识星球，点击文件下载，观察网络请求获取：
1. 文件下载 URL 格式
2. 是否需要特殊处理（如触发下载事件）

---

## 注意事项

- 每次下载后随机延时 3-5 秒
- 下载失败时记录日志，跳过继续
- 确保输出目录存在
