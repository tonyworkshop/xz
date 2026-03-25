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
FETCH_EXIT=0
uv run ./src/fetch_topics.py --update 20 --debug >> output/update.log 2>&1 || FETCH_EXIT=$?

if [ "$FETCH_EXIT" -ne 0 ]; then
    log "抓取失败 (exit=$FETCH_EXIT)"
fi

log "导入数据库..."
uv run ./src/import_data.py >> output/update.log 2>&1

log "下载文章..."
uv run ./src/download_resources.py --articles --debug >> output/update.log 2>&1

log "下载图片..."
uv run ./src/download_resources.py --images --debug >> output/update.log 2>&1

log "提交更新..."
git add output/

# 读取统计文件
NEW_TOPICS=0
NEW_COMMENTS=0
[ -f output/.import_stats ] && source output/.import_stats

# 构建 commit message
MSG="auto: update $(date '+%Y-%m-%d %H:%M')"
if [ "$NEW_TOPICS" -gt 0 ] || [ "$NEW_COMMENTS" -gt 0 ]; then
    MSG="$MSG | +${NEW_TOPICS} topics, +${NEW_COMMENTS} comments"
fi

if [ "$FETCH_EXIT" -ne 0 ] || [ -f output/last_error.txt ]; then
    MSG="$MSG | FETCH FAILED"
fi

git commit -m "$MSG" --allow-empty || true
git push

log "检查抓取结果..."
uv run ./src/check_fetch_result.py >> output/update.log 2>&1

log "=== 更新完成 ==="
