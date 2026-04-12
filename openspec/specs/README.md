# 设计蓝图

知识星球抓取项目的 capability 规格总览。

## Capabilities

### relative-local-path

资源下载路径使用相对路径存储（相对于 `output/` 目录），确保跨机器可移植。`import_data.py` 在导入时自动修复已有的绝对路径。
