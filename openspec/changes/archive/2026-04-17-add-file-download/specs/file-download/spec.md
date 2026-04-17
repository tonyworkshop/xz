## ADDED Requirements

### Requirement: `download_resources.py` 支持下载 topic 关联的文件资源

`download_resources.py` SHALL 支持下载 `files` 表中 `downloaded = 0` 的文件资源，流程与现有 images / articles 下载对等。

#### Scenario: 默认模式下载所有类型的未下载资源
- **WHEN** 运行 `uv run python src/download_resources.py`（不带类型参数）
- **THEN** 脚本按顺序下载所有未下载的 images、articles 和 files

#### Scenario: `--files` 参数仅下载文件
- **WHEN** 运行 `uv run python src/download_resources.py --files`
- **THEN** 脚本仅下载 `files` 表中 `downloaded = 0` 的记录，不触发 images 和 articles 下载

#### Scenario: `--limit` 参数限制文件下载数量
- **WHEN** 运行 `uv run python src/download_resources.py --files --limit 3`
- **THEN** 脚本最多下载 3 个文件后停止

### Requirement: 下载 URL 通过星球 API 动态获取

下载单个文件时，`download_resources.py` SHALL 先调用 `https://api.zsxq.com/v2/files/{file_id}/download_url` 获取临时签名 URL，然后再下载该 URL 指向的二进制内容。

#### Scenario: API 调用成功
- **WHEN** 下载某个文件，API 返回 `{"succeeded": true, "resp_data": {"download_url": "<签名 URL>"}}`
- **THEN** 脚本使用该 URL 下载文件二进制内容并写入 `output/files/` 目录

#### Scenario: API 返回未成功
- **WHEN** API 返回 `succeeded = false` 或 `resp_data.download_url` 缺失
- **THEN** 脚本记录 warning 日志、跳过该文件、继续下一个文件，`downloaded` 保持为 0

#### Scenario: API 调用在页面上下文中执行
- **WHEN** 脚本调用 `download_url` API
- **THEN** 请求通过 Playwright 页面上下文发起（例如 `page.evaluate(fetch(...))`），复用页面 JS 自动注入的 `x-signature` 和 `x-timestamp` 头

### Requirement: 文件按可读名称落盘

下载成功的文件 SHALL 以 `{file_id}_{sanitized_name}` 格式保存到 `output/files/` 目录，其中 `sanitized_name` 是将文件系统保留字符（`/ \ : * ? " < > |`）替换后的 `name` 字段。

#### Scenario: PDF 文件保存为可读文件名
- **WHEN** 下载 `file_id=415514888242148`、`name="For QQQAI Token Holder（2026.4.15）.pdf"` 的文件
- **THEN** 落盘路径为 `output/files/415514888242148_For QQQAI Token Holder（2026.4.15）.pdf`

#### Scenario: 文件名包含保留字符时被替换
- **WHEN** 下载的文件 `name` 包含 `/` 或 `:` 等保留字符
- **THEN** 落盘前将这些字符替换为 `_`

### Requirement: 下载状态持久化到数据库

下载成功后，`download_resources.py` SHALL 将 `files` 表对应记录的 `downloaded` 置为 1，`local_path` 写入相对于 `output/` 的路径。

#### Scenario: 下载成功后状态更新
- **WHEN** 某个文件下载成功并写入磁盘
- **THEN** `UPDATE files SET downloaded = 1, local_path = 'files/{filename}' WHERE file_id = ?` 被执行并 commit

#### Scenario: 已下载的文件不会重复下载
- **WHEN** 运行下载脚本时 `files.downloaded = 1`
- **THEN** 该文件不会被 `get_pending_files()` 选中，跳过下载
