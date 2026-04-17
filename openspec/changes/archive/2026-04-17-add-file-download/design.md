## Context

现有 `download_resources.py` 已有两个下载函数：

```
images    → page.goto(original_url)            → response.body()
articles  → page.goto(inline_article_url)      → page.content() (HTML)
files     → ✗ 未实现（打印"暂不支持"）
```

images / articles 的 URL 是 topic JSON 里就带的，而 files 的 topic JSON 只有 `file_id` / `name` / `hash` / `size`，没有可直接访问的 URL。通过 MCP Playwright 抓包已经确认：

1. 调 `GET https://api.zsxq.com/v2/files/{file_id}/download_url` 返回 `{"succeeded": true, "resp_data": {"download_url": "https://files.zsxq.com/...?e=<unix_ts>&token=<sig>"}}`
2. 返回的 URL 是临时签名，有效期约 1 小时
3. 鉴权走 Cookie（持久化 Playwright context 自带），`x-signature` / `x-timestamp` 由页面 JS 自动注入

## Goals / Non-Goals

**Goals:**
- 下载的文件和现有 images / articles 走同一套 `download_resources.py` 流程
- 复用 `.browser_data/` 登录态，不引入新依赖
- 数据库 schema 保持不动
- 失败单文件不影响整批

**Non-Goals:**
- 不逆向 `x-signature` 算法——直接借页面上下文
- 不持久化 `download_url`（临时签名，存下来下次也用不了）
- 不为已有 18 个文件做特殊 backfill——通用 `downloaded=0` 循环自动覆盖
- 不做断点续传、不做并发（知识星球有频控风险，串行 + 随机延时即可）
- 不做进度条 UI 升级

## Decisions

### Decision 1: 在浏览器上下文中调 API，不自己造签名

**Choice:** 用 `page.evaluate("fetch('/v2/files/{id}/download_url', {credentials: 'include'})")` 直接在页面里发请求，签名头由页面 JS 自动注入。

**Why:**
- `x-signature` 是 JS 算出来的，Python 侧复现要逆向，成本高且易失效
- 页面 JS 会给所有 fetch 自动加签名，白嫖最省事
- images / articles 目前走的 `page.goto()` 也是隐式在浏览器上下文里，思路一致

**Alternative considered:** 用 Python 的 `requests` 加 Cookie 直接调 API——被否，`x-signature` 绕不过去。

### Decision 2: 两步下载拆两次 `page.goto`

**Choice:**
```python
1. resp = page.evaluate(fetch download_url API)  → dict
2. download_url = resp["resp_data"]["download_url"]
3. page.goto(download_url) → response.body()     → 二进制写盘
```

**Why:**
- 第二步的 `files.zsxq.com` URL 是开放 CDN，不需要签名头，`page.goto` 直出二进制最省事
- 和 `download_image` 完全同构

### Decision 3: 文件名用数据库的 `name` 字段，加文件系统安全处理

**Choice:** `safe_filename = f"{file_id}_{sanitize(name)}"`，`sanitize` 只替换文件系统保留字符（`/ \ : * ? " < > |`）。

**Why:**
- 用户期望落盘文件名可读（带原名）
- 加 `file_id` 前缀避免同名覆盖
- 全角括号 / 中文 / 空格在 macOS 和 Linux 都合法，不需要转义
- `CLAUDE.md` 原文档写的是"直接用 `name` 字段"，但不加前缀同名会碰撞

**Alternative:** 只用 `file_id.<ext>`——被否，失去可读性。

### Decision 4: `files` 表不加字段

**Choice:** `download_url` 不入库，每次下载现调 API。

**Why:**
- URL 有 ~1 小时过期，存下来没有复用价值
- 少一列少一处要维护的状态
- `downloaded` / `local_path` 已经够用

### Decision 5: 失败处理

**Choice:** 单文件异常捕获，打 warning 继续下一个。API 返回 `succeeded=false` 时视为失败、跳过。

**Why:** 和现有 `download_image` / `download_article` 行为一致。18 个文件里如果某个挂了不应该阻塞其他。

## Risks / Trade-offs

- **签名 URL 过期**：拿到 URL 后如果中间因延时等 >1h 才去 `page.goto`——概率极小（我们是 API 返回后立即 goto），若命中就失败跳过。Mitigation: 不把 URL 持久化；每个文件走完 "取 URL → 下载" 再延时。
- **频控风险**：批量下载可能被星球限流。Mitigation: 复用现有 3-5s 随机延时。
- **API 协议变更**：`/v2/files/{id}/download_url` 或 `resp_data.download_url` 键名可能被改。Mitigation: 返回结构用 `resp.get("resp_data", {}).get("download_url")` 防御式取值，缺失时走失败分支。
- **未登录态**：如果 `.browser_data/` Cookie 失效，API 会返回未授权。Mitigation: 现有 images / articles 也依赖登录态，行为一致；失败会在日志里体现。
