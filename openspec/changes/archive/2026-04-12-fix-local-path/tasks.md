## 1. 修改 download_resources.py 存储相对路径

- [x] 1.1 将图片下载后写入 DB 的 `local_path` 从 `str(local_path)` 改为相对于 `OUTPUT_DIR` 的相对路径
- [x] 1.2 将文章下载后写入 DB 的 `local_path` 从 `str(local_path)` 改为相对于 `OUTPUT_DIR` 的相对路径

## 2. 在 import_data.py 中添加路径迁移逻辑

- [x] 2.1 新增 `migrate_local_paths(conn)` 函数：遍历 `images`、`articles`、`files` 三张表，将以 `/` 开头的绝对路径修复为相对路径（提取 `/output/` 之后的部分），跳过无法解析的路径并打印警告
- [x] 2.2 在 `import_all()` 末尾调用 `migrate_local_paths(conn)`
