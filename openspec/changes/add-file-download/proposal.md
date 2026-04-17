## Why

`download_resources.py` 目前只支持下载图片和文章，文件（PDF / 音频等）下载是空缺的——`--files` 参数会直接打印"暂不支持"。数据库里已经有 18 个文件记录等待下载，通用下载流程缺一块能力。现在已经抓包确认了下载 URL 的获取方式，可以把文件下载补齐，让 `download_resources.py` 真正做到"遇到 topic 有未下载的资源就全部下载"。

## What Changes

- `download_resources.py` 新增 `get_pending_files()` 和 `download_file()` 函数，和现有 `images` / `articles` 代码同构
- `--files` 参数从占位实装为真实下载
- 默认模式（不带 `--images` / `--articles` / `--files`）自动覆盖文件下载
- 数据库 schema **不变**：`files` 表已有 `downloaded` / `local_path` 字段
- 不持久化下载 URL（临时签名，每次现取现用）

## Capabilities

### New Capabilities
- `file-download`: 从知识星球下载 topic 关联的文件资源（PDF、音频等），复用登录态，先调 `download_url` API 拿签名 URL 再下载

### Modified Capabilities
<!-- 无 -->

## Impact

- 代码：`src/download_resources.py`
- 依赖：无新增（复用 Playwright + 已有数据库模块）
- API 访问：新增对 `https://api.zsxq.com/v2/files/{file_id}/download_url` 的调用
- 副作用：每次下载会在星球后台留下下载记录（与普通用户点击下载行为一致）
- 兼容性：非破坏性，现有 images / articles 流程完全不动
