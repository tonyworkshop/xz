#!/usr/bin/env node
/**
 * 知识星球内容下载工具 - 主入口
 */

import type { Topic, SyncMode, SyncState } from './types.js';
import { ZsxqScraper } from './scraper.js';
import { downloadImages, downloadFiles } from './downloader.js';
import { generateMarkdown, saveAsMarkdown } from './markdown.js';
import {
  loadConfig,
  loadSyncState,
  saveSyncState,
  log,
  logError,
  logSuccess,
  logProgress,
  formatDuration,
  randomDelay,
} from './utils.js';

/**
 * 处理单个帖子
 * @param scraper 可选，用于获取完整评论
 */
async function processTopic(topic: Topic, outputDir: string, scraper?: import('./scraper.js').ZsxqScraper): Promise<void> {
  try {
    log(`处理帖子: ${topic.topic_id}`);

    // 通过详情 API 获取完整评论（列表页不含子回复）
    if (scraper) {
      const fullComments = await scraper.fetchTopicComments(topic);
      if (fullComments && fullComments.length > 0) {
        topic.comments = fullComments;
        log(`已更新评论: ${fullComments.length} 条`);
      }
    }

    // 下载图片
    let imagePaths: string[] = [];
    if (topic.type === 'q&a' && topic.answer?.images) {
      imagePaths = await downloadImages(topic.answer.images, outputDir, topic.topic_id);
    } else if (topic.talk?.images) {
      imagePaths = await downloadImages(topic.talk.images, outputDir, topic.topic_id);
    } else if (topic.answer?.images) {
      imagePaths = await downloadImages(topic.answer.images, outputDir, topic.topic_id);
    }

    // 下载文件
    let filePaths: Array<{ name: string; path: string }> = [];
    if (topic.talk?.files) {
      filePaths = await downloadFiles(topic.talk.files, outputDir, topic.topic_id);
    }

    // 生成 Markdown
    const markdown = generateMarkdown(topic, imagePaths, filePaths);

    // 保存文件
    saveAsMarkdown(topic, markdown, outputDir);

    logSuccess(`帖子处理完成: ${topic.topic_id}`);
  } catch (error) {
    logError(`处理帖子失败: ${topic.topic_id}`, error);
  }
}

/**
 * 全量同步（流式处理：边滚动边下载）
 * @param limit 可选，限制总共处理的帖子数量
 */
async function fullSync(limit?: number): Promise<void> {
  const config = loadConfig();
  const syncState = loadSyncState();
  const scraper = new ZsxqScraper(config.group_id);
  const fullSyncStartTime = Date.now();

  try {
    log('========================================');
    if (limit) {
      log(`开始全量同步（流式模式：处理 ${limit} 个帖子后停止）`);
    } else {
      log('开始全量同步（流式模式）');
    }
    log('========================================');

    // 检查是否有未完成的下载（断点续传）
    const resumeFromTime = syncState.full_sync_progress?.in_progress
      ? syncState.full_sync_progress.oldest_time
      : null;

    if (resumeFromTime) {
      log(`⚠️  检测到未完成的下载`);
      log(`📍 将从上次中断位置继续（最早时间: ${resumeFromTime}）`);
      log(`📊 已下载: ${syncState.full_sync_progress?.total_downloaded || 0} 个帖子\n`);
    }

    // 标记开始下载
    syncState.full_sync_progress = {
      in_progress: true,
      oldest_time: resumeFromTime,
      total_downloaded: Object.keys(syncState.synced_topics).length,
    };
    saveSyncState(syncState);

    await scraper.init();
    await scraper.navigateToGroup();

    let processedCount = 0;
    const startTime = Date.now();

    // 流式处理：边滚动边处理
    await scraper.loadTopicsStream(resumeFromTime, async (batchTopics) => {
      // 过滤已处理的帖子
      const unprocessed = batchTopics.filter(
        t => !syncState.synced_topics[t.topic_id]
      );

      if (unprocessed.length === 0) {
        return { stop: false };
      }

      log(`\n📥 本批新增 ${unprocessed.length} 个未处理帖子`);

      for (const topic of unprocessed) {
        processedCount++;

        const title = topic.talk?.text?.substring(0, 30) || topic.answer?.text?.substring(0, 30) || topic.question?.text?.substring(0, 30) || '无标题';
        const limitInfo = limit ? `/${limit}` : '';
        log(`\n[${processedCount}${limitInfo}] 处理: ${title}...`);

        await processTopic(topic, config.output_dir, scraper);

        // 帖子间随机延时（跳过最后一个）
        if (topic !== unprocessed[unprocessed.length - 1]) {
          await randomDelay(5000, 8000);
        }

        // 更新同步状态
        syncState.synced_topics[topic.topic_id] = {
          last_updated: topic.create_time,
          comment_count: topic.comments_count || topic.comments?.length || 0,
        };

        // 每处理 5 个保存一次状态
        if (processedCount % 5 === 0) {
          saveSyncState(syncState);
        }

        if (limit && processedCount >= limit) {
          return { stop: true };
        }
      }

      // 更新断点进度：记录当前批次中最早的时间
      const sorted = [...batchTopics].sort(
        (a, b) => new Date(a.create_time).getTime() - new Date(b.create_time).getTime()
      );
      syncState.full_sync_progress = {
        in_progress: true,
        oldest_time: sorted[0].create_time,
        total_downloaded: Object.keys(syncState.synced_topics).length,
      };
      saveSyncState(syncState);
      log(`💾 保存进度: 已处理到 ${sorted[0].create_time}`);

      return { stop: false };
    });

    // 判断是否全部完成（无 limit 或 limit 未达到说明滚动到底了）
    const reachedLimit = limit && processedCount >= limit;

    syncState.last_sync_time = new Date().toISOString();

    if (!reachedLimit) {
      // 滚动到底了，全部完成
      syncState.full_sync_progress = {
        in_progress: false,
        oldest_time: null,
        total_downloaded: 0,
      };
    }

    saveSyncState(syncState);

    const totalElapsedSeconds = (Date.now() - fullSyncStartTime) / 1000;
    const totalElapsedTime = formatDuration(totalElapsedSeconds);

    log('\n========================================');
    if (processedCount === 0) {
      logSuccess('没有新内容需要处理！');
    } else if (reachedLimit) {
      logSuccess(`已处理 ${processedCount} 个帖子（达到限制），可再次运行继续`);
    } else {
      logSuccess(`全量同步完成！共处理 ${processedCount} 个帖子`);
    }
    log(`📊 统计信息:`);
    log(`  - 本次处理: ${processedCount} 个帖子`);
    log(`  - 总耗时: ${totalElapsedTime}`);
    if (processedCount > 0) {
      log(`  - 平均速度: ${(processedCount / totalElapsedSeconds * 60).toFixed(1)} 个/分钟`);
    }
    log(`  - 输出目录: ${config.output_dir}`);
    if (reachedLimit) {
      log(`\n💡 提示: 再次运行相同命令可继续下载`);
    }
    log('========================================');
  } catch (error) {
    logError('全量同步失败', error);
    log('\n💡 提示: 再次运行 /xz full 可以从中断位置继续下载');
    throw error;
  } finally {
    await scraper.close();
  }
}

/**
 * 增量同步
 */
async function incrementalSync(): Promise<void> {
  const config = loadConfig();
  const syncState = loadSyncState();
  const scraper = new ZsxqScraper(config.group_id);
  const incrementalSyncStartTime = Date.now();

  try {
    log('========================================');
    log('开始增量同步（最新 20 条）');
    log('========================================');

    // 抓取最新 20 个帖子
    const latestTopics = await scraper.scrape();
    log(`抓取到 ${latestTopics.length} 个最新帖子`);

    // 按时间降序排序（最新优先）
    latestTopics.sort((a, b) =>
      new Date(b.create_time).getTime() - new Date(a.create_time).getTime()
    );

    // 检查更新
    let newTopics = 0;
    let updatedTopics = 0;

    const topicsToProcess: Topic[] = [];

    for (const topic of latestTopics) {
      const syncedTopic = syncState.synced_topics[topic.topic_id];

      if (!syncedTopic) {
        // 新帖子
        newTopics++;
        topicsToProcess.push(topic);
        log(`发现新帖子: ${topic.topic_id}`);
      } else {
        const currentCommentCount = topic.comments?.length || 0;
        const syncedCommentCount = syncedTopic.comment_count;

        if (currentCommentCount > syncedCommentCount) {
          // 有新评论
          updatedTopics++;
          topicsToProcess.push(topic);
          log(`帖子有新评论: ${topic.topic_id} (${syncedCommentCount} -> ${currentCommentCount})`);
        }
      }
    }

    log(`\n需要处理的帖子:`);
    log(`  - 新帖子: ${newTopics}`);
    log(`  - 有更新的帖子: ${updatedTopics}`);

    if (topicsToProcess.length === 0) {
      logSuccess('没有新内容需要同步');
      return;
    }

    // 处理需要更新的帖子
    log('\n========================================');
    log(`📥 开始下载和生成 Markdown...`);
    log(`📊 总数: ${topicsToProcess.length} 个帖子`);
    log('========================================\n');

    const startTime = Date.now();

    for (let i = 0; i < topicsToProcess.length; i++) {
      const topic = topicsToProcess[i];
      const currentIndex = i + 1;

      // 显示当前处理的帖子标题
      const title = topic.talk?.text?.substring(0, 30) || topic.answer?.text?.substring(0, 30) || topic.question?.text?.substring(0, 30) || '无标题';
      log(`\n[${currentIndex}/${topicsToProcess.length}] 处理: ${title}...`);

      await processTopic(topic, config.output_dir, scraper);

      // 帖子间随机延时（跳过最后一个）
      if (i < topicsToProcess.length - 1) {
        await randomDelay(5000, 8000);
      }

      // 显示进度信息
      logProgress(currentIndex, topicsToProcess.length, startTime, '总进度');
    }

    // 更新同步状态
    for (const topic of topicsToProcess) {
      syncState.synced_topics[topic.topic_id] = {
        last_updated: topic.create_time,
        comment_count: topic.comments_count || topic.comments?.length || 0,
      };
    }

    syncState.last_sync_time = new Date().toISOString();
    saveSyncState(syncState);

    const totalElapsedSeconds = (Date.now() - incrementalSyncStartTime) / 1000;
    const totalElapsedTime = formatDuration(totalElapsedSeconds);

    log('\n========================================');
    logSuccess('增量同步完成!');
    log(`📊 统计信息:`);
    log(`  - 处理帖子: ${topicsToProcess.length} 个 (${newTopics} 新, ${updatedTopics} 更新)`);
    log(`  - 总耗时: ${totalElapsedTime}`);
    log(`  - 输出目录: ${config.output_dir}`);
    log('========================================');
  } catch (error) {
    logError('增量同步失败', error);
    throw error;
  } finally {
    await scraper.close();
  }
}

/**
 * 打开浏览器并保持运行（用于手动检查、登录、调试）
 */
async function openBrowser(): Promise<void> {
  const config = loadConfig();
  const scraper = new ZsxqScraper(config.group_id);

  const cleanup = async () => {
    log('\n正在关闭浏览器...');
    await scraper.close();
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  try {
    await scraper.init();
    await scraper.navigateToGroup();

    log('\n浏览器已打开，按 Ctrl+C 退出');
    await new Promise(() => {});
  } catch (error) {
    logError('打开浏览器失败', error);
    await scraper.close();
    process.exit(1);
  }
}

/**
 * 主函数
 */
async function main() {
  // 解析命令行参数
  const args = process.argv.slice(2);
  const modeArg = args.find((arg) => arg.startsWith('--mode='));
  const mode: SyncMode = modeArg?.split('=')[1] as SyncMode || 'incremental';

  // 解析 limit 参数
  const limitArg = args.find((arg) => arg.startsWith('--limit='));
  const limit = limitArg ? parseInt(limitArg.split('=')[1], 10) : undefined;

  log('知识星球内容下载工具');
  log(`模式: ${mode === 'open' ? '打开浏览器' : mode === 'full' ? '全量同步' : '增量同步'}`);
  if (limit && mode === 'full') {
    log(`限制: 每次处理 ${limit} 个帖子`);
  }
  log('');

  try {
    if (mode === 'open') {
      await openBrowser();
    } else if (mode === 'full') {
      await fullSync(limit);
    } else {
      await incrementalSync();
    }

    process.exit(0);
  } catch (error) {
    logError('执行失败', error);
    process.exit(1);
  }
}

// 运行主函数
main();
