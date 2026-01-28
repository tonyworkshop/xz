# 修复评论子回复缺失 — 状态记录

## 已完成

- `src/parser.ts`：已清理 `[DEBUG]` 日志；已导出 `normalizeComments`
- `src/index.ts`：`processTopic` 已改为无条件调用 `fetchTopicComments`；已删除 `navigateBackToGroup` 调用
- `src/scraper.ts`：已删除 `fetchTopicDetails` 和 `navigateBackToGroup` 方法
- 确认了详情页实际调用的 API URL：
  - `/v2/topics/{id}/info` — 帖子信息
  - `/v2/topics/{id}/comments?sort=asc&count=30&with_sticky=true` — 评论列表

## 遇到的问题

### API 签名头阻止直接调用

知识星球 API 需要 `x-signature`、`x-timestamp`、`x-request-id`、`x-aduid` 等动态签名头。这些头由站点 JS 的 axios 拦截器自动添加。

- `page.evaluate(fetch(...))` → `succeeded=false, code=1007`
- `page.evaluate(XMLHttpRequest)` → `succeeded=false, code=1059`
- 复用拦截到的请求头 → 签名是 per-request 的，复用无效
- 页面无全局 `axios` / `Vue` 实例可调用

### 当前页导航方案的问题

在 `fetchTopicComments` 中导航到详情页再导航回来，会丢失主页的滚动位置，导致全量同步流程中断。

## 待实施：新标签页方案

在同一浏览器上下文（`this.context`）中 `context.newPage()` 开新标签页：
1. 新标签页共享 cookie 和签名逻辑
2. 在新标签页中导航到 `topic_detail/{id}` 页面
3. 站点 JS 会自动带签名头调用 API
4. 通过 `detailPage.on('response')` 捕获 `/topics/{id}/comments` 端点响应
5. 用 `normalizeComments()` 解析评论数据（含子回复）
6. 关闭新标签页，主页滚动状态完全不受影响

### 改动范围

只需改 `src/scraper.ts`：
- 重写 `fetchTopicComments` 方法（用新标签页 + response 监听）
- 清理调试代码：删除 `_headersPrinted`、`apiHeaders` 字段和 `[NET]`/`[DEBUG]` 日志

### 验证步骤

1. 清空 `output/` + `.xz/sync_state.json`
2. 运行 `npx tsx src/index.ts --mode=full --limit=3`
3. 检查有评论帖子的 markdown 是否包含嵌套子回复
4. 确认滚动加载没有被中断
