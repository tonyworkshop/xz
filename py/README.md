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

### 评论抓取：模态框方式（v2）

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
    4. 关闭模态框（Escape 键）
    ↓
继续滚动主页面...
```

优势：
- 不离开主页面，保持 DOM 状态
- 模态框内滚动触发 comments API
- 关闭模态框后可继续处理下一个 topic

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

#### 4. 评论加载完成检测

通过 API 响应判断是否还有更多评论：

```python
comments = data.get("resp_data", {}).get("comments", [])
count = int(query.get("count", [30])[0])
if len(comments) == 0 or len(comments) < count:
    comments_finished = True  # 返回数量少于请求数量，说明已加载完毕
```

## 使用方法

```bash
# 仅打开浏览器（用于登录）
python py/fetch_topics.py --open

# 手动模式（登录后手动滚动）
python py/fetch_topics.py

# 自动模式（自动滚动抓取所有内容）
python py/fetch_topics.py --auto

# 自动模式 + 等待登录
python py/fetch_topics.py --auto --wait-login=30
```

## 输出

```
output/
  json/
    topics/     # topics API 响应
    comments/   # comments API 响应
```

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
