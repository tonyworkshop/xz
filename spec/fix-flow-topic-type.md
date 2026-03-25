# Fix: 支持 type="flow" 的 topic

## 问题

mini 机器上 `update.sh` 运行到 index=9 的 topic 时 crash。

**crash log** (`mini_output/update.log:83223-83226`):
```
[ERROR] [严重错误] app-topic index=9 没有 content 元素!
  contentType: None
  outerHTML 片段: <app-topic type="flow" ...><div class="topic-container">...
[ERROR] 已保存 click_cache，程序退出。请检查页面结构。
```

## 原因

`fetch_topics.py:98-102` 的 `get_all_topic_keys` 只识别两种 content 子元素：
- `app-answer-content` → type "answer"
- `app-talk-content` → type "talk"

遇到 `type="flow"` 的 `app-topic` 时，找不到 content 元素，`hasContent=false`，`key=null`。

当前 master 代码（commit 502936a）已改为跳过未知类型（不再 crash），但 **flow 类型的 topic 仍然不会被处理**。

## 待调查

**需要用 MCP Playwright 打开浏览器检查 `type="flow"` 的 DOM 结构：**

1. flow 类型 topic 的 content 子元素叫什么？（猜测 `app-flow-content`，需确认）
2. flow 类型 topic 是否有"查看详情"按钮？（`div.details-container .text`）
3. flow 类型的模态框结构是否与 talk/answer 一致？（`div.topic-detail`）
4. flow 类型在 API 数据中的 type 字段值是什么？（已查 topics JSON，现有数据全是 talk/q&a，没有 flow）

## 修改范围

**文件**: `src/fetch_topics.py`

**改动点**: `get_all_topic_keys` 函数 (line 88-112) 中的 JS 代码，需要：
- 增加对 flow 类型 content 元素的查找
- 或改为通用方式：读取 `app-topic` 的 `type` attribute，动态构造 selector `app-{type}-content`

## 验证

1. MCP 浏览器确认 flow DOM 结构
2. 修改代码后在 mini 上 `git pull` + 重新运行 `update.sh`
3. 确认 flow 类型 topic 能正常处理（点击→模态框→评论→关闭）
