# 设计蓝图

知识星球抓取项目的 capability 规格总览。

## Capabilities

### relative-local-path

资源下载路径使用相对路径存储（相对于 `output/` 目录），确保跨机器可移植。`import_data.py` 在导入时自动修复已有的绝对路径。

### file-download

`download_resources.py` 支持下载 topic 关联的文件资源（PDF、音频等），和 images / articles 对等。通过 `/v2/files/{file_id}/download_url` API 拿临时签名 URL，在 Playwright 页面上下文执行（复用登录态和 JS 签名），再用 APIRequestContext 下载二进制落盘至 `output/files/{file_id}_{safe_name}`。
