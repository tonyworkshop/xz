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
├── run.sh
├── update.sh
├── open.sh
├── .gitignore
├── .python-version     # Python 版本
├── .venv/              # 虚拟环境（uv 自动创建）
├── src/
│   ├── fetch_topics.py # 主脚本
│   ├── config.toml     # 配置（星球 ID）
│   └── .browser_data/  # 浏览器持久化数据（登录状态）
├── input/
└── output/
    ├── topics/         # topics API 响应 JSON
    └── comments/       # comments API 响应 JSON

## 运行方式
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
