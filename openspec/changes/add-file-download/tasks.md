## 1. 实装下载逻辑

- [ ] 1.1 在 `src/download_resources.py` 新增 `sanitize_filename(name: str) -> str` 工具函数，替换文件系统保留字符
- [ ] 1.2 新增 `get_pending_files(conn, limit=None)` 函数，查询 `files.downloaded = 0` 的记录
- [ ] 1.3 新增 `download_file(page, conn, file)` 函数，实现两步下载：
  - 用 `page.evaluate` 调 `/v2/files/{file_id}/download_url` API
  - 校验 `succeeded` 和 `resp_data.download_url` 存在
  - `page.goto(download_url)` 获取二进制，写入 `output/files/{file_id}_{safe_name}`
  - 更新 `downloaded = 1` 和 `local_path` 并 commit

## 2. 接入命令行参数和主流程

- [ ] 2.1 移除 `main()` 中 `--files` 的"暂不支持"分支和 warning
- [ ] 2.2 在 `main()` 中加入 `files = get_pending_files(...) if (download_all or args.files) else []`
- [ ] 2.3 打印待下载文件统计（与 images / articles 对齐）
- [ ] 2.4 在浏览器 context 中加入文件下载循环，失败单个不阻塞整批，每个文件后走 `random_delay`
- [ ] 2.5 在完成提示里加入 `FILES_DIR` 路径

## 3. 验证

- [ ] 3.1 运行 `uv run python src/download_resources.py --files --limit 1`，确认单文件下载成功
- [ ] 3.2 `file output/files/*.pdf` 确认至少一个有效 PDF
- [ ] 3.3 `sqlite3 output/xz.db "SELECT downloaded, local_path FROM files WHERE downloaded = 1 LIMIT 3"` 确认状态写入
- [ ] 3.4 再跑一次同命令，确认已下载的不会重复拉（`get_pending_files` 过滤生效）
- [ ] 3.5 全量 `uv run python src/download_resources.py --files` 把 18 个文件跑完，统计成功数
