# Python 抓取脚本

## 概述

`fetch_topics.py` 通过 Playwright 浏览器自动化抓取知识星球的 topics 和 comments 数据。

## 核心设计思路

### 数据获取方式：网络拦截

**不直接调用 API**，而是通过 `page.on("response")` 拦截浏览器的网络请求：

```python
page.on("response", handle_response)
```

优势：
- 无需管理认证 token（复用浏览器登录态）
- 规避反爬检测（请求由真实浏览器发起）
- 数据结构与官方 API 一致

### 持久化浏览器：免重复登录

使用 Playwright 的 `launch_persistent_context` 保存浏览器状态：

```python
context = p.chromium.launch_persistent_context(
    user_data_dir=str(USER_DATA_DIR),  # .browser_data 目录
    headless=False,
    # ...
)
```

优势：
- Cookies、localStorage 持久化保存
- 首次登录后，后续运行无需重新登录
- 登录状态保存在 `py/.browser_data/` 目录

### 评论抓取：模态框方式

#### 为什么不用 `page.goto()` 导航？

最初设计是对每个 topic 导航到详情页：
```python
# 旧方案（已弃用）
topic_url = f"https://wx.zsxq.com/group/{GROUP_ID}/topic/{topic_id}"
page.goto(topic_url)  # 导航到详情页
# 滚动加载评论...
page.goto(TARGET_URL)  # 返回主页面
```

问题：
1. 每次导航都会重新加载页面，丢失已加载的 topics 列表
2. 返回主页面后需要重新滚动到之前的位置
3. 频繁导航增加被检测风险

#### 新方案：点击打开模态框

```
滚动主页面 → 网络拦截捕获 topics API → 收集 {topic_id, text}
    ↓
对每个 topic：
    1. 通过文本匹配在页面中定位该帖子
    2. 点击"查看详情"按钮打开模态框
    3. 在模态框内滚动 → 触发 comments API 请求 → 网络拦截捕获
    4. 关闭模态框（点击遮罩区域）
    5. 随机延时 5-8 秒
    ↓
继续滚动主页面...
```

优势：
- 不离开主页面，保持 DOM 状态
- 模态框内滚动触发 comments API
- 关闭模态框后可继续处理下一个 topic

### 反检测措施

1. **随机延时**：
   - Topic 间隔：5-8 秒（`random.randint(5000, 8000)`）
   - 滚动间隔：1-2 秒
   - 模态框内滚动：1.5 秒

2. **真实 User-Agent**：
   ```python
   user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
   ```

3. **持久化浏览器**：行为特征与真实用户一致

### 关键实现细节

#### 1. 保存文本用于匹配

从 API 响应中提取帖子文本，用于后续在页面中定位：

```python
text = (topic.get("talk", {}).get("text") or
        topic.get("question", {}).get("text") or
        topic.get("answer", {}).get("text") or "")
pending_topics.append({"topic_id": topic_id, "text": text[:50]})
```

#### 2. 通过文本匹配定位帖子

```python
def find_topic_button(page, text_snippet: str):
    match_index = page.evaluate('''(searchText) => {
        const topics = document.querySelectorAll('app-topic');
        for (let i = 0; i < topics.length; i++) {
            if (topics[i].textContent.includes(searchText)) return i;
        }
        return -1;
    }''', text_snippet)
    # 获取该 app-topic 内的"查看详情"按钮
    button = page.evaluate_handle('''(idx) => {
        const topics = document.querySelectorAll('app-topic');
        return topics[idx]?.querySelector('div.details-container .text');
    }''', match_index)
    return button.as_element()
```

#### 3. 模态框内滚动

```python
def scroll_modal_for_comments(page):
    page.evaluate('''() => {
        const modal = document.querySelector('div.topic-detail');
        if (modal) modal.scrollTop = modal.scrollHeight;
    }''')
```

注意：是 `modal.scrollTop`，不是 `window.scrollTo`。

#### 4. 关闭模态框：点击遮罩区域

```python
def close_modal(page):
    modal = page.query_selector('div.topic-detail')
    if modal:
        box = modal.bounding_box()
        # 点击模态框左侧外部的遮罩区域
        click_x = max(10, box['x'] - 50)
        click_y = box['y'] + 100
        page.mouse.click(click_x, click_y)
```

为什么不用 Escape 键或点击关闭按钮？
- 遮罩点击更可靠，模拟真实用户行为
- 关闭按钮选择器可能不稳定

#### 5. 评论加载完成检测

通过 API 响应判断是否还有更多评论：

```python
comments = data.get("resp_data", {}).get("comments", [])
count = int(query.get("count", [30])[0])
if len(comments) == 0 or len(comments) < count:
    comments_finished = True  # 返回数量少于请求数量，说明已加载完毕
```

#### 6. 自动停止条件

```python
no_new_topics_count = 0
max_no_new_attempts = 5  # 连续 5 次滚动没有新 topics 则认为到底
```

## 使用方法

```bash
# 仅打开浏览器（用于首次登录）
python py/fetch_topics.py --open

# 手动模式（登录后手动滚动，脚本只负责拦截保存）
python py/fetch_topics.py

# 自动模式（自动滚动抓取所有内容）
python py/fetch_topics.py --auto

# 自动模式 + 等待登录（给 30 秒时间扫码登录）
python py/fetch_topics.py --auto --wait-login=30

# 启用详细日志（调试用）
python py/fetch_topics.py --auto --wait-login=30 --debug
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--open` | 仅打开浏览器，不拦截请求（用于登录） |
| `--auto` | 自动模式，自动滚动抓取所有内容 |
| `--wait-login=N` | 自动模式下等待 N 秒进行登录 |
| `--debug` | 启用 DEBUG 级别日志（详细） |
| `--info` | 启用 INFO 级别日志（默认） |

### 典型工作流

1. **首次使用**：
   ```bash
   python py/fetch_topics.py --open
   # 在浏览器中扫码登录，确认登录成功后 Ctrl+C 退出
   ```

2. **后续抓取**（已登录状态会保持）：
   ```bash
   python py/fetch_topics.py --auto
   ```

3. **调试问题**：
   ```bash
   python py/fetch_topics.py --auto --debug
   ```

## 输出

```
output/
  json/
    topics/     # topics API 响应
    comments/   # comments API 响应
```

文件命名格式：
- Topics: `{group_id}_{timestamp}.json`
- Comments: `{topic_id}_{timestamp}.json`

## DOM 选择器参考

| 元素 | 选择器 |
|------|--------|
| 帖子容器 | `app-topic` |
| 查看详情按钮 | `div.details-container .text` |
| 模态框 | `div.topic-detail` |
| 关闭按钮 | `div.topic-detail .close-btn` |

## 调试验证

按照 CLAUDE.md 要求，使用 MCP Playwright 工具验证：

```
1. browser_navigate → 打开知识星球页面
2. browser_snapshot → 查看 DOM 结构
3. browser_evaluate → 测试选择器
4. browser_click → 测试点击按钮
5. browser_network_requests → 确认 API 拦截
```

## 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                         启动浏览器                               │
│              launch_persistent_context(.browser_data)            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    导航到知识星球页面                             │
│                    注册 response 拦截器                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │         主循环开始              │
          └───────────────┬───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     滚动主页面                                   │
│            window.scrollTo(0, document.body.scrollHeight)        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              网络拦截器捕获 topics API 响应                       │
│                 保存 JSON + 加入待处理队列                        │
│              pending_topics.append({topic_id, text})             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │    处理待处理队列中的每个 topic  │
          └───────────────┬───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. find_topic_button() - 通过文本匹配定位帖子                    │
│  2. click_detail_button() - 点击"查看详情"打开模态框              │
│  3. scroll_modal_for_comments() - 模态框内滚动加载评论            │
│     └─ 网络拦截器捕获 comments API 响应并保存                     │
│  4. close_modal() - 点击遮罩区域关闭模态框                        │
│  5. 随机延时 5-8 秒                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │  连续 5 次无新 topics？         │
          │  是 → 结束    否 → 继续滚动     │
          └───────────────────────────────┘
```

## 常见问题

### Q: 登录状态丢失？
A: 检查 `py/.browser_data/` 目录是否存在。如果删除了该目录需要重新登录。

### Q: 评论加载不完整？
A: 启用 `--debug` 查看详细日志，确认 `comments_finished` 标志是否正确设置。

### Q: 抓取速度太快被限制？
A: 当前 topic 间隔为 5-8 秒，如需更保守可修改 `process_pending_comments()` 中的 `random.randint(5000, 8000)`。

### Q: 模态框关闭失败？
A: 脚本会自动回退到按 Escape 键关闭。如果仍有问题，检查模态框选择器 `div.topic-detail` 是否正确。
