/**
 * Markdown 生成器
 */

import { writeFileSync } from 'fs';
import { join } from 'path';
import {
  ensureDir,
  sanitizeFilename,
  formatDateTime,
  formatDateForFilename,
  log,
} from './utils.js';
import type { Topic, Comment, Reply } from './types.js';

/**
 * 生成 Markdown 内容
 */
export function generateMarkdown(
  topic: Topic,
  imagePaths: string[],
  filePaths: Array<{ name: string; path: string }>
): string {
  const lines: string[] = [];

  // Frontmatter
  const title = extractTitle(topic);
  const sourceUrl = `https://wx.zsxq.com/dweb2/index/topic_detail/${topic.topic_id}`;

  lines.push('---');
  lines.push(`title: "${title}"`);
  lines.push(`date: ${topic.create_time}`);
  lines.push(`topic_id: ${topic.topic_id}`);
  lines.push(`source: ${sourceUrl}`);
  lines.push(`type: ${topic.type}`);
  if (topic.likes_count) {
    lines.push(`likes: ${topic.likes_count}`);
  }
  if (topic.comments_count) {
    lines.push(`comments: ${topic.comments_count}`);
  }
  lines.push('---');
  lines.push('');

  // 标题
  lines.push(`# ${title}`);
  lines.push('');

  // 元信息
  lines.push(`**发布时间**: ${formatDateTime(topic.create_time)}`);
  if (topic.likes_count) {
    lines.push(`**点赞数**: ${topic.likes_count}`);
  }
  lines.push('');

  // 主内容
  if (topic.type === 'talk' && topic.talk) {
    lines.push('## 内容');
    lines.push('');
    lines.push(topic.talk.text || '');
    lines.push('');

    // 图片
    if (imagePaths.length > 0) {
      for (const imagePath of imagePaths) {
        lines.push(`![图片](${imagePath})`);
        lines.push('');
      }
    }

    // 文件
    if (filePaths.length > 0) {
      lines.push('### 附件');
      lines.push('');
      for (const file of filePaths) {
        lines.push(`- [${file.name}](${file.path})`);
      }
      lines.push('');
    }
  } else if (topic.type === 'question' && topic.question) {
    lines.push(`## 提问 | ${topic.author.name || '匿名用户'}`);
    lines.push('');
    lines.push(topic.question.text || '');
    lines.push('');
  } else if (topic.type === 'answer' && topic.answer) {
    lines.push('## 回答 | 许哲');
    lines.push('');
    lines.push(topic.answer.text || '');
    lines.push('');

    // 图片
    if (imagePaths.length > 0) {
      for (const imagePath of imagePaths) {
        lines.push(`![图片](${imagePath})`);
        lines.push('');
      }
    }
  } else if (topic.type === 'q&a') {
    if (topic.question) {
      lines.push(`## 提问 | ${topic.author.name || '匿名用户'}`);
      lines.push('');
      lines.push(topic.question.text || '');
      lines.push('');
    }
    if (topic.answer) {
      lines.push('## 回答 | 许哲');
      lines.push('');
      lines.push(topic.answer.text || '');
      lines.push('');
      if (imagePaths.length > 0) {
        for (const imagePath of imagePaths) {
          lines.push(`![图片](${imagePath})`);
          lines.push('');
        }
      }
    }
  }

  // 评论
  if (topic.comments && topic.comments.length > 0) {
    lines.push('---');
    lines.push('');
    lines.push('## 评论');
    lines.push('');

    for (const comment of topic.comments) {
      lines.push(...generateCommentMarkdown(comment));
    }
  }

  return lines.join('\n');
}

/**
 * 生成评论的 Markdown
 */
function generateCommentMarkdown(comment: Comment): string[] {
  const lines: string[] = [];

  // 评论标题
  const commentTime = formatDateTime(comment.create_time);
  lines.push(`### ${comment.owner.name} - ${commentTime}`);
  lines.push('');

  // 回复对象
  if (comment.repliee) {
    lines.push(`> 回复 @${comment.repliee.name}`);
    lines.push('');
  }

  // 评论内容
  lines.push(comment.text);
  lines.push('');

  // 评论中的图片（如果有）
  if (comment.images && comment.images.length > 0) {
    for (const image of comment.images) {
      const imageUrl =
        image.large?.url || image.large_url || image.original?.url;
      if (imageUrl) {
        lines.push(`![评论图片](${imageUrl})`);
        lines.push('');
      }
    }
  }

  // 回复
  if (comment.replies && comment.replies.length > 0) {
    for (const reply of comment.replies) {
      lines.push(...generateReplyMarkdown(reply));
    }
  }

  lines.push('');

  return lines;
}

/**
 * 生成回复的 Markdown
 */
function generateReplyMarkdown(reply: Reply): string[] {
  const lines: string[] = [];

  const replyTime = formatDateTime(reply.create_time);
  lines.push(`#### ${reply.owner.name} - ${replyTime}`);
  lines.push('');

  // 回复对象
  if (reply.repliee) {
    lines.push(`> 回复 @${reply.repliee.name}`);
    lines.push('');
  }

  // 回复内容
  lines.push(reply.text);
  lines.push('');

  return lines;
}

/**
 * 提取标题
 */
function extractTitle(topic: Topic): string {
  let text = '';

  if (topic.type === 'talk' && topic.talk) {
    text = topic.talk.text || '';
  } else if (topic.type === 'question' && topic.question) {
    text = topic.question.text || '';
  } else if (topic.type === 'answer' && topic.answer) {
    text = topic.answer.text || '';
  } else if (topic.type === 'q&a') {
    text = topic.answer?.text || topic.question?.text || '';
  }

  // 取前 50 个字符作为标题
  const title = text
    .replace(/\n/g, ' ')
    .trim()
    .substring(0, 50);

  return title || '无标题';
}

/**
 * 生成文件名
 */
export function generateFilename(topic: Topic): string {
  const datePrefix = formatDateForFilename(topic.create_time);
  const title = extractTitle(topic);
  const safeTitle = sanitizeFilename(title);

  return `${datePrefix}_${safeTitle}.md`;
}

/**
 * 保存为 Markdown 文件
 */
export function saveAsMarkdown(
  topic: Topic,
  content: string,
  outputDir: string
): string {
  ensureDir(outputDir);

  const filename = generateFilename(topic);
  const filepath = join(outputDir, filename);

  writeFileSync(filepath, content, 'utf-8');

  log(`已保存: ${filename}`);

  return filepath;
}
