### Requirement: 资源下载路径使用相对路径存储

`download_resources.py` 写入数据库的 `local_path` 字段 SHALL 使用相对于 `output/` 目录的相对路径。

格式示例：
- 图片：`images/123456.jpg`
- 文章：`articles/abc123.html`
- 文件：`files/report.pdf`

#### Scenario: 新下载的图片存储相对路径
- **WHEN** `download_resources.py` 下载一张图片并更新 `images` 表
- **THEN** `local_path` 为 `images/{image_id}.{image_type}` 格式的相对路径

#### Scenario: 新下载的文章存储相对路径
- **WHEN** `download_resources.py` 下载一篇文章并更新 `articles` 表
- **THEN** `local_path` 为 `articles/{article_id}.html` 格式的相对路径

### Requirement: 导入时自动修复已有绝对路径

`import_data.py` 的 `import_all()` SHALL 在导入完成后检查并修复 `images`、`articles`、`files` 三张表中的绝对路径。

#### Scenario: 修复包含 output/ 的绝对路径
- **WHEN** 数据库中某条记录的 `local_path` 为 `/Users/mini/dev/xz/output/articles/abc.html`
- **THEN** 修复为 `articles/abc.html`

#### Scenario: 跳过已经是相对路径的记录
- **WHEN** 数据库中某条记录的 `local_path` 为 `articles/abc.html`（不以 `/` 开头）
- **THEN** 不做修改

#### Scenario: 跳过无法解析的绝对路径
- **WHEN** 数据库中某条记录的 `local_path` 为绝对路径但不包含 `/output/`
- **THEN** 跳过该记录并打印警告
