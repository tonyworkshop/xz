# 知识星球抓取脚本

## plan mode
不要给我代码，首先我们先讨论思路，思路跟我确认没问题后，再给我代码

## 技术栈
- Python 3.11+ (tomllib 内置)
- Playwright (浏览器自动化)
- TOML (配置文件)

## 项目结构
xz/
├── CLAUDE.md
├── pyproject.toml      # Python 项目配置
├── uv.lock             # 依赖锁定
├── run.sh              # 全量抓取 + 导入
├── update.sh           # 增量抓取 + 导入
├── open.sh
├── todo.md             # 待办事项
├── .gitignore
├── .python-version     # Python 版本
├── .venv/              # 虚拟环境（uv 自动创建）
├── src/
│   ├── fetch_topics.py      # 抓取脚本
│   ├── import_data.py       # JSON 导入数据库
│   ├── download_resources.py # 资源下载脚本
│   ├── db.py                # 数据库操作模块
│   ├── config.toml          # 配置（星球 ID）
│   └── .browser_data/       # 浏览器持久化数据（登录状态）
├── input/
└── output/
    ├── topics/         # topics API 响应 JSON
    ├── comments/       # comments API 响应 JSON
    ├── xz.db           # SQLite 数据库
    ├── images/         # 下载的图片
    ├── files/          # 下载的文件（PDF/音频）
    └── articles/       # 下载的文章 HTML

## 运行方式

### 抓取数据
# 首次：打开浏览器登录
uv run python src/fetch_topics.py --open

# 默认：自动全量抓取
uv run python src/fetch_topics.py

# 更新抓取（最新 N 个）
uv run python src/fetch_topics.py --update 30

# 手动模式（仅拦截，用户自己滚动）
uv run python src/fetch_topics.py --manual

# 手动模式 + 限制（抓 N 个后停止）
uv run python src/fetch_topics.py --update 30 --manual

# 等待登录后自动抓取
uv run python src/fetch_topics.py --wait-login=30

### 导入数据库
uv run python src/import_data.py

### 下载资源
# 下载全部（图片 + 文章）
uv run python src/download_resources.py

# 仅下载图片
uv run python src/download_resources.py --images

# 仅下载文章
uv run python src/download_resources.py --articles

# 限制下载数量（测试用）
uv run python src/download_resources.py --limit 5

# 启用调试日志
uv run python src/download_resources.py --debug

## 浏览器调试与验证
**禁止使用 `uv run python src/fetch_topics.py` 启动浏览器进行调试验证。**
必须通过 MCP Playwright 工具进行交互测试。

原因：MCP 操作浏览器时，Claude Code 能直接获取页面快照、DOM 结构、网络请求，
自主判断页面状态、定位问题。而脚本启动的浏览器是独立进程，Claude Code 无法感知页面内容。

## 核心设计
- **网络拦截**：page.on("response") 捕获 API，无需管理 token
- **持久化浏览器**：launch_persistent_context 保存登录状态
- **模态框抓取**：点击帖子 → 打开模态框 → 滚动加载评论 → 关闭
- **反检测**：5-8秒随机延时、真实 User-Agent

## DOM 选择器
| 元素 | 选择器 |
|------|--------|
| 帖子容器 | `app-topic` |
| 查看详情按钮 | `div.details-container .text` |
| 模态框 | `div.topic-detail` |

## 资源下载原则

**核心约束：资源需要登录后才能下载**
- ❌ 禁止直接用 `requests` / `httpx` / `aiohttp` 发 HTTP 请求
- ✅ 必须使用 Playwright 浏览器，复用 `.browser_data/` 中的登录状态
- ✅ 通过 `page.goto(url)` 导航到资源 URL，获取响应内容

### 资源类型与 URL
| 资源 | URL 字段 | 文件名规则 |
|------|----------|-----------|
| images | `original_url` | `{image_id}.{image_type}` |
| articles | `inline_article_url` | `{article_id}.html` |
| files | 待抓包确认 | 直接用 `name` 字段 |

### 下载状态追踪
数据库中每个资源表都有：
- `downloaded` (INTEGER): 0=未下载, 1=已下载
- `local_path` (TEXT): 本地存储路径

导入脚本不会重置已下载状态。
