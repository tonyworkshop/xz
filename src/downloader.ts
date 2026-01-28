/**
 * 附件下载器
 */

import { writeFileSync } from 'fs';
import { join } from 'path';
import { ensureDir, getExtensionFromUrl, sanitizeFilename, log, logError } from './utils.js';
import type { Image, File as ZsxqFile } from './types.js';

/**
 * 下载图片
 */
export async function downloadImage(
  url: string,
  outputDir: string,
  topicId: string,
  index: number
): Promise<string> {
  try {
    const imagesDir = join(outputDir, 'images');
    ensureDir(imagesDir);

    // 提取文件扩展名
    const ext = getExtensionFromUrl(url);
    const filename = `${topicId}_${index}.${ext}`;
    const filepath = join(imagesDir, filename);

    // 下载图片
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const buffer = await response.arrayBuffer();
    writeFileSync(filepath, Buffer.from(buffer));

    log(`已下载图片: ${filename}`);

    // 返回相对路径用于 Markdown 引用
    return `images/${filename}`;
  } catch (error) {
    logError(`下载图片失败: ${url}`, error);
    // 如果下载失败，返回原始 URL
    return url;
  }
}

/**
 * 下载文件
 */
export async function downloadFile(
  file: ZsxqFile,
  outputDir: string,
  topicId: string,
  index: number
): Promise<string> {
  try {
    const filesDir = join(outputDir, 'files');
    ensureDir(filesDir);

    // 使用原始文件名或生成安全的文件名
    const ext = file.name.split('.').pop() || 'bin';
    const safeName = sanitizeFilename(file.name);
    const filename = `${topicId}_${index}_${safeName}`;
    const filepath = join(filesDir, filename);

    // 下载文件
    const response = await fetch(file.download_url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const buffer = await response.arrayBuffer();
    writeFileSync(filepath, Buffer.from(buffer));

    log(`已下载文件: ${filename}`);

    // 返回相对路径用于 Markdown 引用
    return `files/${filename}`;
  } catch (error) {
    logError(`下载文件失败: ${file.name}`, error);
    // 如果下载失败，返回原始 URL
    return file.download_url;
  }
}

/**
 * 批量下载图片
 */
export async function downloadImages(
  images: Image[] | undefined,
  outputDir: string,
  topicId: string
): Promise<string[]> {
  if (!images || images.length === 0) {
    return [];
  }

  const results: string[] = [];

  for (let i = 0; i < images.length; i++) {
    const image = images[i];
    const url = image.large?.url || image.large_url || image.original?.url;

    if (!url) {
      continue;
    }

    const path = await downloadImage(url, outputDir, topicId, i);
    results.push(path);
  }

  return results;
}

/**
 * 批量下载文件
 */
export async function downloadFiles(
  files: ZsxqFile[] | undefined,
  outputDir: string,
  topicId: string
): Promise<Array<{ name: string; path: string }>> {
  if (!files || files.length === 0) {
    return [];
  }

  const results: Array<{ name: string; path: string }> = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const path = await downloadFile(file, outputDir, topicId, i);
    results.push({
      name: file.name,
      path,
    });
  }

  return results;
}

/**
 * 获取图片 URL
 */
export function getImageUrl(image: Image): string | null {
  return image.large?.url || image.large_url || image.original?.url || null;
}
