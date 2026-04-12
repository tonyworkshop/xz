## Why

`download_resources.py` 将资源的 `local_path` 以绝对路径存入数据库（如 `/Users/mini/dev/xz/output/articles/lbs7ewna2t6n.html`），导致在不同机器或目录间迁移项目时路径失效。

## What Changes

- `download_resources.py` 中写入 `images`、`articles`、`files` 表的 `local_path` 从绝对路径改为相对于 `output/` 目录的相对路径（如 `articles/lbs7ewna2t6n.html`）
- 在 `import_data.py` 执行时，自动修复数据库中已有的绝对路径为相对路径

## Capabilities

### New Capabilities

- `relative-local-path`: 资源下载路径使用相对路径存储，确保跨机器可移植

### Modified Capabilities

## Impact

- `src/download_resources.py`: 修改 `local_path` 的生成逻辑
- `src/import_data.py`: 新增数据库迁移逻辑，修复已有绝对路径
- `output/xz.db`: 现有数据中 `images.local_path`、`articles.local_path`、`files.local_path` 会被更新
