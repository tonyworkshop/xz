## Context

`download_resources.py` 下载图片和文章后，将 `local_path` 以 `str(Path(...))` 形式写入数据库，产生绝对路径（如 `/Users/mini/dev/xz/output/articles/xxx.html`）。项目在不同机器间迁移时路径失效。

当前涉及三张表：`images`、`articles`、`files`，均有 `local_path` 字段。

## Goals / Non-Goals

**Goals:**
- `local_path` 统一使用相对于 `output/` 的相对路径（如 `articles/xxx.html`、`images/123.jpg`）
- 已有数据库中的绝对路径自动修复为相对路径

**Non-Goals:**
- 不改变文件的实际存储位置
- 不改变 `downloaded` 状态判断逻辑

## Decisions

1. **相对路径基准：相对于 `output/` 目录**
   - `images/123.jpg` 而非 `./output/images/123.jpg`
   - 理由：`output/` 是所有资源的根目录，使用方拼接 `OUTPUT_DIR / local_path` 即可得到完整路径

2. **迁移逻辑放在 `import_data.py`**
   - 在 `import_all()` 中导入数据后执行一次路径修复
   - 理由：`import_data.py` 是每次更新都会运行的入口，且已有数据库写入权限；`db.py` 只负责单条记录操作，不适合放批量迁移
   - 迁移逻辑：检测 `local_path` 是否以 `/` 开头，如果是则提取 `output/` 之后的部分

3. **`download_resources.py` 直接存相对路径**
   - 用 `Path(local_path).relative_to(OUTPUT_DIR)` 得到相对路径后再存入数据库

## Risks / Trade-offs

- **[已下载资源路径不包含 `output/`]** → 如果某条 `local_path` 格式异常（不包含 `/output/`），迁移时跳过并打印警告，不破坏原有数据
