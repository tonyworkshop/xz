#!/bin/bash
set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> output/update.log
}

log "=== 开始更新 ==="

log "抓取最新话题..."
uv run ./src/fetch_topics.py --update 20 --debug >> output/update.log 2>&1

log "导入数据库..."
uv run ./src/import_data.py >> output/update.log 2>&1

log "下载文章..."
uv run ./src/download_resources.py --articles --debug >> output/update.log 2>&1

log "下载图片..."
uv run ./src/download_resources.py --images --debug >> output/update.log 2>&1

log "提交更新..."
git add output/
git commit -m "auto: update $(date '+%Y-%m-%d %H:%M')" --allow-empty || true
git push

log "=== 更新完成 ==="
