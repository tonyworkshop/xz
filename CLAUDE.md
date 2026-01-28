# ZSXQ Downloader - 知识星球内容下载工具

从"天上不会掉馅饼"星球（group_id: 28888825825151）下载特定作者 **许哲** 的帖子及评论，保存为本地 Markdown + 图片/附件。

## plan mode
不要给我代码，首先我们先讨论思路，思路跟我确认没问题后，再给我代码

## 技术栈

- TypeScript 5.3 + Node.js (ESM, ES2022)
- Playwright 1.40.0 — 浏览器自动化，通过网络拦截捕获 API 数据
- date-fns 3.0.0 — 日期处理
- 构建/运行：tsx 4.0.0

## 项目结构

```
.xz/                  # 配置和同步状态
  config.json           # group_id、target_author、output_dir 等
  sync_state.json       # 已同步 topic、进度、断点信息
src/
  index.ts              # 入口，协调流程，解析命令行参数
  scraper.ts            # Playwright 浏览器自动化，网络请求拦截，滚动加载
  parser.ts             # 过滤许哲相关内容（作者帖子 + 评论回复）
  markdown.ts           # 生成 Markdown（frontmatter、图片引用、评论线程）
  downloader.ts         # 下载图片和附件到本地
  utils.ts              # 日志、文件操作、进度条、状态管理
  types.ts              # TypeScript 类型定义
skill/
  xz.md                 # Claude Code /xz 命令脚本
output/                 # 生成内容
  images/               # 下载的图片
  files/                # 下载的附件
  [YYYY-MM-DD_HHmm_*.md]  # 生成的 Markdown 文件
```

## 数据流

```
Playwright 启动浏览器 → 导航到星球页面（需登录）
  → 网络拦截捕获 /topics API 响应
  → 滚动加载内容（full）或加载最近 N 条（incremental）
  → 去重 → 过滤许哲内容
  → 对每个 topic：下载图片/附件 → 生成 Markdown → 保存文件
  → 更新 sync_state.json
```

## 同步模式

- **full** — 滚动加载全部历史，支持断点续传（tracking oldest_time）
- **incremental** — 仅检查最近 20 条帖子更新
- **batch** (`full --limit=N`) — 每次处理 N 条未处理内容

## 运行方式

```bash
npx tsx src/index.ts                        # 增量同步（默认）
npx tsx src/index.ts --mode=full            # 全量同步
npx tsx src/index.ts --mode=full --limit=10 # 批量，每次 10 条
```

## 浏览器调试与验证

**禁止使用 `npx tsx src/index.ts` 启动浏览器进行调试验证。** 必须通过 MCP Playwright 工具（`browser_navigate`、`browser_snapshot`、`browser_evaluate`、`browser_click` 等）打开浏览器进行交互测试。

原因：通过 MCP 操作浏览器时，Claude Code 能直接获取页面快照、DOM 结构、网络请求等内容，从而自主判断页面状态、定位问题并调整代码。而 `npx` 启动的浏览器是独立进程，Claude Code 无法感知其中的页面内容，只能看到终端输出的日志，无法自行排查 DOM 选择器、模态框行为、API 拦截等问题。

典型验证流程：
1. `browser_navigate` 导航到目标页面
2. `browser_evaluate` 检查 DOM 元素是否存在、属性是否正确
3. `browser_click` / `browser_evaluate` 触发交互（如点击按钮）
4. `browser_snapshot` 或 `browser_evaluate` 确认交互结果
5. `browser_network_requests` 检查 API 请求是否被正确拦截

## 关键设计

- **网络拦截**：通过 `page.on('response')` 捕获 API 响应，无需直接管理认证 token
- **断点续传**：sync_state.json 记录进度，中断后从上次位置继续；每处理 5 条保存一次状态
- **内容过滤**：检查帖子作者 + 递归扫描评论/回复中的许哲内容
- **反检测**：随机延时 2-3 秒、真实 User-Agent
- **容错**：图片下载失败时回退为 URL 引用，局部失败不中断整体流程
