# 知识星球抓取脚本 (Python)

通过 Playwright 浏览器自动化抓取知识星球的 topics 和 comments 数据。

## 项目结构

```
py/
├── config.toml         # 配置文件（星球 ID 等）
├── fetch_topics.py     # 主脚本
├── .browser_data/      # 浏览器持久化数据（登录状态）
├── pyproject.toml      # Python 项目配置
└── .venv/              # 虚拟环境
```

## 配置

`config.toml`（支持注释）：

```toml
# 知识星球配置
group_id = "28888825825151"  # 许哲的星球
# group_id = "1824528822"    # 其他星球
```

## 输出目录

```
output/
├── topics/      # topics API 响应 JSON
└── comments/    # comments API 响应 JSON
```

文件命名：
- Topics: `{group_id}_{timestamp}.json`
- Comments: `{topic_id}_{page_id}.json`

## 使用方法

```bash
# 1. 首次使用：打开浏览器登录
python py/fetch_topics.py --open
# 扫码登录后 Ctrl+C 退出

# 2. 自动抓取（已登录状态会保持）
python py/fetch_topics.py --auto

# 3. 等待登录后自动抓取
python py/fetch_topics.py --auto --wait-login=30

# 4. 手动模式（只拦截保存，手动滚动）
python py/fetch_topics.py

# 5. 调试模式
python py/fetch_topics.py --auto --debug
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--open` | 仅打开浏览器，不拦截请求（用于登录） |
| `--auto` | 自动模式，自动滚动抓取所有内容 |
| `--wait-login=N` | 自动模式下等待 N 秒进行登录 |
| `--debug` | 启用 DEBUG 级别日志 |

## 核心设计

### 1. 网络拦截（非 API 调用）

通过 `page.on("response")` 拦截浏览器请求，无需管理认证 token：

```python
page.on("response", handle_response)
```

### 2. 持久化浏览器

使用 `launch_persistent_context` 保存登录状态到 `.browser_data/`：

```python
context = p.chromium.launch_persistent_context(
    user_data_dir=str(USER_DATA_DIR),
    headless=False,
)
```

### 3. 模态框方式抓取评论

不使用 `page.goto()` 导航（会丢失 DOM 状态），而是：

```
滚动主页面 → 拦截 topics API → 收集 {topic_id, text}
    ↓
对每个 topic：
    1. 通过文本匹配定位帖子
    2. 点击"查看详情"打开模态框
    3. 模态框内滚动 → 触发 comments API
    4. 关闭模态框（点击遮罩）
    5. 随机延时 5-8 秒
```

### 4. 配置文件读取

使用 Python 3.11+ 内置 `tomllib` 读取 TOML 配置：

```python
import tomllib

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)

CONFIG = load_config()
GROUP_ID = CONFIG["group_id"]
```

## 数据流

```
启动浏览器 (persistent_context)
    ↓
导航到星球页面 + 注册 response 拦截
    ↓
┌─────────────────────────────────────┐
│            主循环                    │
│  1. 滚动页面                         │
│  2. 拦截 topics API → 保存 JSON      │
│  3. 对每个 topic:                    │
│     - 点击打开模态框                  │
│     - 滚动加载评论                    │
│     - 拦截 comments API → 保存 JSON  │
│     - 关闭模态框                     │
│  4. 连续 5 次无新内容 → 结束          │
└─────────────────────────────────────┘
```

## 反检测措施

- Topic 间隔：5-8 秒随机延时
- 滚动间隔：1-2 秒
- 真实 User-Agent
- 持久化浏览器（行为特征一致）

## DOM 选择器

| 元素 | 选择器 |
|------|--------|
| 帖子容器 | `app-topic` |
| 查看详情按钮 | `div.details-container .text` |
| 模态框 | `div.topic-detail` |

## 常见问题

**Q: 登录状态丢失？**
A: 检查 `.browser_data/` 目录是否存在，删除后需重新登录。

**Q: 评论加载不完整？**
A: 使用 `--debug` 查看详细日志。

**Q: 抓取太快被限制？**
A: 修改 `process_pending_comments()` 中的延时参数。

**Q: 模态框关闭失败？**
A: 脚本会自动回退到 Escape 键关闭。

## 技术栈

- Python 3.11+（内置 `tomllib`）
- Playwright（浏览器自动化）
- TOML（配置文件，支持注释）
