/**
 * 工具函数
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { Config, SyncState } from './types.js';

const CONFIG_PATH = '/Users/tony/dev/personal/xz/.xz/config.json';
const STATE_PATH = '/Users/tony/dev/personal/xz/output/sync_state.json';

/**
 * 加载配置文件
 */
export function loadConfig(): Config {
  try {
    const content = readFileSync(CONFIG_PATH, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error('加载配置文件失败:', error);
    throw error;
  }
}

/**
 * 加载同步状态
 */
export function loadSyncState(): SyncState {
  try {
    if (!existsSync(STATE_PATH)) {
      return {
        last_sync_time: null,
        synced_topics: {},
        xu_zhe_user_id: null,
      };
    }
    const content = readFileSync(STATE_PATH, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.error('加载同步状态失败:', error);
    return {
      last_sync_time: null,
      synced_topics: {},
      xu_zhe_user_id: null,
    };
  }
}

/**
 * 保存同步状态
 */
export function saveSyncState(state: SyncState): void {
  try {
    const dir = dirname(STATE_PATH);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(STATE_PATH, JSON.stringify(state, null, 2), 'utf-8');
  } catch (error) {
    console.error('保存同步状态失败:', error);
    throw error;
  }
}

/**
 * 确保目录存在
 */
export function ensureDir(dir: string): void {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

/**
 * 生成安全的文件名（移除不合法字符）
 */
export function sanitizeFilename(filename: string): string {
  return filename
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, '_')
    .substring(0, 100);
}

/**
 * 延迟函数
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 随机延迟（模拟人类行为）
 */
export function randomDelay(min: number, max: number): Promise<void> {
  const ms = min + Math.random() * (max - min);
  return delay(ms);
}

/**
 * 从 URL 提取文件扩展名
 */
export function getExtensionFromUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;
    const match = pathname.match(/\.(\w+)$/);
    return match ? match[1] : 'jpg';
  } catch {
    return 'jpg';
  }
}

/**
 * 格式化日期时间
 */
export function formatDateTime(dateString: string): string {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * 格式化日期（用于文件名）
 */
export function formatDateForFilename(dateString: string): string {
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}_${hours}${minutes}`;
}

/**
 * 日志函数
 */
export function log(message: string, ...args: any[]): void {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${message}`, ...args);
}

export function logError(message: string, error?: any): void {
  const timestamp = new Date().toISOString();
  console.error(`[${timestamp}] ❌ ${message}`, error || '');
}

export function logSuccess(message: string): void {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ✅ ${message}`);
}

/**
 * 格式化时长（秒）为可读字符串
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}秒`;
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}分${secs}秒`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}小时${mins}分`;
  }
}

/**
 * 生成进度条
 */
export function generateProgressBar(current: number, total: number, width: number = 30): string {
  const percentage = Math.min(100, Math.round((current / total) * 100));
  const filledWidth = Math.round((current / total) * width);
  const emptyWidth = width - filledWidth;

  const filled = '█'.repeat(filledWidth);
  const empty = '░'.repeat(emptyWidth);

  return `[${filled}${empty}] ${percentage}%`;
}

/**
 * 计算预估剩余时间
 */
export function estimateRemainingTime(
  processed: number,
  total: number,
  elapsedSeconds: number
): string {
  if (processed === 0) {
    return '计算中...';
  }

  const avgTimePerItem = elapsedSeconds / processed;
  const remaining = total - processed;
  const estimatedSeconds = avgTimePerItem * remaining;

  return formatDuration(estimatedSeconds);
}

/**
 * 打印进度信息
 */
export function logProgress(
  current: number,
  total: number,
  startTime: number,
  prefix: string = '进度'
): void {
  const elapsedSeconds = (Date.now() - startTime) / 1000;
  const progressBar = generateProgressBar(current, total);
  const remaining = estimateRemainingTime(current, total, elapsedSeconds);
  const elapsed = formatDuration(elapsedSeconds);

  log(`${prefix}: ${current}/${total} ${progressBar} | 已用时: ${elapsed} | 预计剩余: ${remaining}`);
}
