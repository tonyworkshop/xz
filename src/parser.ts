/**
 * 数据解析器 - 筛选和处理许哲相关的内容
 */

import type { Page } from 'playwright';
import type { Topic, Comment, Reply } from './types.js';
import { log } from './utils.js';

const TARGET_AUTHOR = '许哲';

/**
 * 检查帖子是否包含许哲的内容
 */
export function hasXuZheContent(topic: Topic): boolean {
  // 1. 检查是否是许哲发布的帖子
  if (topic.author.name === TARGET_AUTHOR) {
    return true;
  }

  // 2. 检查评论中是否有许哲的内容
  if (topic.comments && topic.comments.length > 0) {
    for (const comment of topic.comments) {
      if (isXuZheComment(comment)) {
        return true;
      }
    }
  }

  return false;
}

/**
 * 检查评论是否是许哲发表的
 */
function isXuZheComment(comment: Comment): boolean {
  // 检查评论作者
  if (comment.owner.name === TARGET_AUTHOR) {
    return true;
  }

  // 检查回复中是否有许哲的回复
  if (comment.replies && comment.replies.length > 0) {
    for (const reply of comment.replies) {
      if (reply.owner.name === TARGET_AUTHOR) {
        return true;
      }
    }
  }

  return false;
}

/**
 * 筛选许哲相关的内容
 */
export function filterXuZheContent(topics: Topic[]): Topic[] {
  const filtered: Topic[] = [];

  for (const topic of topics) {
    if (hasXuZheContent(topic)) {
      filtered.push(topic);
    }
  }

  log(`筛选结果: ${filtered.length}/${topics.length} 个帖子包含许哲的内容`);

  return filtered;
}

/**
 * 筛选许哲的评论（从帖子中提取）
 */
export function filterXuZheComments(topic: Topic): Comment[] {
  if (!topic.comments || topic.comments.length === 0) {
    return [];
  }

  const filtered: Comment[] = [];

  for (const comment of topic.comments) {
    if (isXuZheComment(comment)) {
      filtered.push(comment);
    }
  }

  return filtered;
}

/**
 * 标准化 Topic 数据结构
 * 处理 API 返回的不同格式
 */
export function normalizeTopic(rawTopic: any): Topic {
  const topic: Topic = {
    topic_id: rawTopic.topic_id || rawTopic.id,
    create_time: rawTopic.create_time || rawTopic.created_at,
    author: {
      user_id: rawTopic.owner?.user_id || rawTopic.author?.user_id || rawTopic.question?.owner?.user_id || '',
      name: rawTopic.owner?.name || rawTopic.author?.name || rawTopic.question?.owner?.name || '',
      avatar_url: rawTopic.owner?.avatar_url || rawTopic.author?.avatar_url || rawTopic.question?.owner?.avatar_url,
    },
    type: rawTopic.type || 'talk',
    likes_count: rawTopic.likes?.count || rawTopic.likes_count || 0,
    comments_count: rawTopic.comments?.count || rawTopic.comments_count || 0,
    reads_count: rawTopic.reads_count || 0,
  };

  // 处理 talk 类型
  if (rawTopic.talk) {
    topic.talk = {
      text: rawTopic.talk.text || '',
      images: rawTopic.talk.images || [],
      files: rawTopic.talk.files || [],
    };
  }

  // 处理 question 类型
  if (rawTopic.question) {
    topic.question = {
      text: rawTopic.question.text || '',
      images: rawTopic.question.images || [],
    };
  }

  // 处理 answer 类型
  if (rawTopic.answer) {
    topic.answer = {
      text: rawTopic.answer.text || '',
      images: rawTopic.answer.images || [],
    };
  }

  // 处理评论
  if (rawTopic.show_comments) {
    topic.comments = normalizeComments(rawTopic.show_comments);
  } else if (rawTopic.comments && Array.isArray(rawTopic.comments)) {
    topic.comments = normalizeComments(rawTopic.comments);
  }

  return topic;
}

/**
 * 标准化评论数据
 */
export function normalizeComments(rawComments: any[]): Comment[] {
  if (!Array.isArray(rawComments)) {
    return [];
  }

  return rawComments.map((rawComment) => {
    const comment: Comment = {
      comment_id: rawComment.comment_id || rawComment.id,
      create_time: rawComment.create_time || rawComment.created_at,
      owner: {
        user_id: rawComment.owner?.user_id || '',
        name: rawComment.owner?.name || '',
        avatar_url: rawComment.owner?.avatar_url,
      },
      text: rawComment.text || '',
      images: rawComment.images || [],
    };

    // 处理回复对象
    if (rawComment.repliee) {
      comment.repliee = {
        user_id: rawComment.repliee.user_id || '',
        name: rawComment.repliee.name || '',
      };
    }

    // 处理子回复
    if (rawComment.replies && Array.isArray(rawComment.replies)) {
      comment.replies = rawComment.replies.map((rawReply: any) => {
        const reply: Reply = {
          reply_id: rawReply.reply_id || rawReply.id,
          create_time: rawReply.create_time || rawReply.created_at,
          owner: {
            user_id: rawReply.owner?.user_id || '',
            name: rawReply.owner?.name || '',
            avatar_url: rawReply.owner?.avatar_url,
          },
          text: rawReply.text || '',
          images: rawReply.images || [],
        };

        if (rawReply.repliee) {
          reply.repliee = {
            user_id: rawReply.repliee.user_id || '',
            name: rawReply.repliee.name || '',
          };
        }

        return reply;
      });
    }

    return comment;
  });
}

/**
 * 从 API 响应中提取 topics
 */
export function extractTopicsFromResponse(response: any): Topic[] {
  try {
    // 尝试多种可能的响应格式
    let rawTopics: any[] = [];

    if (response.resp_data?.topics) {
      rawTopics = response.resp_data.topics;
    } else if (response.topics) {
      rawTopics = response.topics;
    } else if (Array.isArray(response)) {
      rawTopics = response;
    }

    // 标准化每个 topic
    return rawTopics.map(normalizeTopic);
  } catch (error) {
    console.error('提取 topics 失败:', error);
    return [];
  }
}

/**
 * 从模态框 HTML 中解析评论
 * 在 div.topic-detail 打开后调用，直接从 DOM 提取全部评论
 */
export async function parseCommentsFromHTML(page: Page): Promise<Comment[]> {
  const rawComments = await page.evaluate(() => {
    // @ts-expect-error - document is available in browser context
    const containers = document.querySelectorAll('.comment-container');
    const results: any[] = [];

    containers.forEach((container: any, idx: number) => {
      // 提取主评论
      const mainItem = container.querySelector('app-comment-item.main-comment-item');
      if (!mainItem) return;

      const author = mainItem.querySelector('span.comment')?.textContent?.trim() || '';
      const text = mainItem.querySelector('span.text[parsetype="pure"]')?.textContent?.trim() || '';
      const time = mainItem.querySelector('.time')?.textContent?.trim() || '';
      const avatarUrl = mainItem.querySelector('img.user-avatar')?.getAttribute('src') || '';

      // 提取回复
      const replyItems = container.querySelectorAll('.reply-comment app-comment-item');
      const replies: any[] = [];

      replyItems.forEach((replyItem: any, rIdx: number) => {
        const replyAuthor = replyItem.querySelector('span.comment')?.textContent?.trim() || '';
        const replyText = replyItem.querySelector('span.text[parsetype="pure"]')?.textContent?.trim() || '';
        const replyTime = replyItem.querySelector('.time')?.textContent?.trim() || '';
        const replyAvatarUrl = replyItem.querySelector('img.user-avatar')?.getAttribute('src') || '';
        const repliee = replyItem.querySelector('span.refer')?.textContent?.trim() || '';

        replies.push({
          replyAuthor,
          replyText,
          replyTime,
          replyAvatarUrl,
          repliee,
          rIdx,
        });
      });

      results.push({ author, text, time, avatarUrl, idx, replies });
    });

    return results;
  });

  // 转换为 Comment[] 类型
  return rawComments.map((raw, idx) => {
    const comment: Comment = {
      comment_id: `html_${idx}_${raw.author}_${raw.time}`,
      create_time: raw.time, // "2026-01-27 22:19" 格式
      owner: {
        user_id: '',
        name: raw.author,
        avatar_url: raw.avatarUrl || undefined,
      },
      text: raw.text,
    };

    if (raw.replies && raw.replies.length > 0) {
      comment.replies = raw.replies.map((r: any) => {
        const reply: Reply = {
          reply_id: `html_${idx}_r${r.rIdx}_${r.replyAuthor}_${r.replyTime}`,
          create_time: r.replyTime,
          owner: {
            user_id: '',
            name: r.replyAuthor,
            avatar_url: r.replyAvatarUrl || undefined,
          },
          text: r.replyText,
        };

        if (r.repliee) {
          reply.repliee = {
            user_id: '',
            name: r.repliee,
          };
        }

        return reply;
      });
    }

    return comment;
  });
}

/**
 * 统计许哲的内容数量
 */
export function countXuZheContent(topics: Topic[]): {
  totalTopics: number;
  xuZheTopics: number;
  xuZheComments: number;
  xuZheReplies: number;
} {
  let xuZheTopics = 0;
  let xuZheComments = 0;
  let xuZheReplies = 0;

  for (const topic of topics) {
    // 统计许哲发布的帖子
    if (topic.author.name === TARGET_AUTHOR) {
      xuZheTopics++;
    }

    // 统计许哲的评论和回复
    if (topic.comments) {
      for (const comment of topic.comments) {
        if (comment.owner.name === TARGET_AUTHOR) {
          xuZheComments++;
        }

        if (comment.replies) {
          for (const reply of comment.replies) {
            if (reply.owner.name === TARGET_AUTHOR) {
              xuZheReplies++;
            }
          }
        }
      }
    }
  }

  return {
    totalTopics: topics.length,
    xuZheTopics,
    xuZheComments,
    xuZheReplies,
  };
}
