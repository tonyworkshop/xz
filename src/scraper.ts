/**
 * 浏览器爬虫核心 - 使用 Playwright 拦截网络请求获取数据
 */

import { chromium, BrowserContext, Page, Response } from 'playwright';
import type { Topic, Comment } from './types.js';
import { extractTopicsFromResponse, parseCommentsFromHTML } from './parser.js';
import { log, logError, logSuccess, randomDelay } from './utils.js';

const USER_DATA_DIR = '/Users/tony/dev/personal/xz/.xz/browser_data';

export class ZsxqScraper {
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private groupId: string;
  private capturedTopics: Topic[] = [];
  constructor(groupId: string) {
    this.groupId = groupId;
  }

  /**
   * 初始化浏览器（持久化上下文，登录一次后自动记住）
   */
  async init(): Promise<void> {
    try {
      log('启动浏览器...');
      this.context = await chromium.launchPersistentContext(USER_DATA_DIR, {
        headless: false,
        userAgent:
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      });

      this.page = this.context.pages()[0] || await this.context.newPage();

      // 在导航前就设置拦截器，确保捕获页面初始加载的 API 响应
      this.setupNetworkInterceptor();

      logSuccess('浏览器启动成功');
    } catch (error) {
      logError('浏览器启动失败', error);
      throw error;
    }
  }

  /**
   * 设置网络拦截器
   */
  private setupNetworkInterceptor(): void {
    if (!this.page) {
      throw new Error('Page 未初始化');
    }

    this.page.on('response', async (response: Response) => {
      const url = response.url();

      // 拦截 topics API 请求
      if (url.includes('/topics') && url.includes(this.groupId)) {
        try {
          const status = response.status();
          if (status === 200) {
            const data = await response.json();
            const topics = extractTopicsFromResponse(data);

            if (topics.length > 0) {
              log(`拦截到 ${topics.length} 个帖子`);
              this.capturedTopics.push(...topics);
            }
          }
        } catch (error) {
          // 忽略非 JSON 响应
        }
      }
    });
  }

  /**
   * 导航到星球页面
   */
  async navigateToGroup(): Promise<void> {
    if (!this.page) {
      throw new Error('Page 未初始化');
    }

    try {
      const url = `https://wx.zsxq.com/dweb2/index/group/${this.groupId}`;
      log(`导航到星球页面\n${url}`);
      await this.page.goto(url, { waitUntil: 'networkidle' });

      // 等待页面加载
      await randomDelay(2000, 3000);

      // 检查是否需要登录
      const needLogin = await this.checkLoginStatus();
      if (needLogin) {
        log('需要登录，请在浏览器中完成登录...');
        log('登录完成后，按回车继续...');

        // 等待用户登录
        await this.waitForLogin();
      }

      logSuccess('成功导航到星球页面');
    } catch (error) {
      logError('导航失败', error);
      throw error;
    }
  }

  /**
   * 检查登录状态
   */
  private async checkLoginStatus(): Promise<boolean> {
    if (!this.page) {
      return true;
    }

    try {
      // 检查页面 URL 是否重定向到登录页
      const currentUrl = this.page.url();
      if (currentUrl.includes('/login') || currentUrl.includes('/signin')) {
        return true;
      }

      // 检查页面是否包含登录相关元素
      const loginButton = await this.page.$('text=登录');
      return loginButton !== null;
    } catch {
      return false;
    }
  }

  /**
   * 等待用户登录
   */
  private async waitForLogin(): Promise<void> {
    if (!this.page) {
      return;
    }

    // 等待 URL 变化，表示登录成功
    await this.page.waitForURL(`**/group/${this.groupId}**`, {
      timeout: 300000, // 5 分钟超时
    });

    log('检测到登录成功');
    await randomDelay(2000, 3000);
  }

  /**
   * 流式加载帖子：每次滚动拦截到新帖子后，通过回调传出本次新增的帖子
   * @param resumeFromTime 可选，从指定时间点继续（断点续传）
   * @param onBatch 回调，接收本次新增的去重帖子，返回 { stop: true } 可提前终止滚动
   */
  async loadTopicsStream(
    resumeFromTime: string | null,
    onBatch: (topics: Topic[]) => Promise<{ stop: boolean }>
  ): Promise<void> {
    if (!this.page) {
      throw new Error('Page 未初始化');
    }

    // 保留导航阶段已捕获的帖子（不清空），拦截器已在 init 中设置

    if (resumeFromTime) {
      log(`从上次中断位置继续加载（最早时间: ${resumeFromTime}）...`);
    } else {
      log('开始全量加载...');
    }

    const seenIds = new Set<string>();
    let lastCount = 0;
    let noChangeCount = 0;
    let scrollCount = 0;

    while (noChangeCount < 3) {
      // 滚动到底部
      await this.page.evaluate(() => {
        // @ts-expect-error - window and document are available in browser context
        window.scrollTo(0, document.body.scrollHeight);
      });

      scrollCount++;

      // 等待加载
      await randomDelay(2000, 3000);

      // 去重后取出本次新增的帖子
      const allUnique = this.deduplicateTopics();
      const newTopics: Topic[] = [];
      for (const t of allUnique) {
        if (!seenIds.has(t.topic_id)) {
          seenIds.add(t.topic_id);
          newTopics.push(t);
        }
      }

      // 日志：时间范围
      let timeRangeInfo = '';
      if (allUnique.length > 0) {
        const sorted = [...allUnique].sort(
          (a, b) => new Date(a.create_time).getTime() - new Date(b.create_time).getTime()
        );
        const oldestDate = new Date(sorted[0].create_time).toLocaleString('zh-CN', {
          year: 'numeric', month: '2-digit', day: '2-digit'
        });
        const newestDate = new Date(sorted[sorted.length - 1].create_time).toLocaleString('zh-CN', {
          year: 'numeric', month: '2-digit', day: '2-digit'
        });
        timeRangeInfo = ` | 时间范围: ${oldestDate} ~ ${newestDate}`;
      }

      log(`📜 第 ${scrollCount} 次滚动 | 已捕获: ${seenIds.size} 个帖子${timeRangeInfo}`);

      // 如果有新帖子，传给回调处理
      if (newTopics.length > 0) {
        const result = await onBatch(newTopics);
        if (result.stop) {
          log('回调请求停止滚动');
          break;
        }
      }

      // 检查是否有新内容
      if (this.capturedTopics.length === lastCount) {
        noChangeCount++;
        log(`无新内容 (${noChangeCount}/3)`);
      } else {
        noChangeCount = 0;
        lastCount = this.capturedTopics.length;
      }

      // 避免无限滚动
      if (scrollCount >= 100) {
        log('达到最大滚动次数，停止加载');
        break;
      }
    }

    logSuccess(`流式加载完成，共捕获 ${seenIds.size} 个帖子`);
  }

  /**
   * 加载最新的 N 个帖子（增量模式）
   */
  async loadLatestTopics(count: number = 20): Promise<Topic[]> {
    if (!this.page) {
      throw new Error('Page 未初始化');
    }

    // 拦截器已在 init 中设置，保留已捕获的帖子

    log(`开始增量加载（最新 ${count} 个帖子）...`);

    // 等待初始内容加载
    await randomDelay(3000, 4000);

    // 可能需要滚动几次以确保加载到足够的内容
    let scrollCount = 0;
    while (this.capturedTopics.length < count && scrollCount < 5) {
      await this.page.evaluate(() => {
        // @ts-expect-error - window and document are available in browser context
        window.scrollTo(0, document.body.scrollHeight);
      });

      scrollCount++;
      log(`第 ${scrollCount} 次滚动，已捕获 ${this.capturedTopics.length} 个帖子`);

      await randomDelay(2000, 3000);
    }

    logSuccess(`增量加载完成，共捕获 ${this.capturedTopics.length} 个帖子`);

    return this.deduplicateTopics();
  }

  /**
   * 去重 topics
   */
  private deduplicateTopics(): Topic[] {
    const uniqueMap = new Map<string, Topic>();

    for (const topic of this.capturedTopics) {
      uniqueMap.set(topic.topic_id, topic);
    }

    return Array.from(uniqueMap.values());
  }

  /**
   * 获取单个帖子的完整评论（模态框方案）
   * 在列表页点击"查看详情"打开模态框，通过网络拦截获取完整评论，
   * 滚动加载全部评论后关闭模态框。
   *
   * 由于 DOM 中无 topicId，采用按顺序点击 + API 识别的方式。
   */
  async fetchTopicComments(topic: Topic): Promise<Comment[] | null> {
    if (!this.page) {
      throw new Error('Page 未初始化');
    }

    const topicId = topic.topic_id;

    try {
      log(`获取帖子完整评论: ${topicId}`);

      // 通过模态框方案获取评论（文本匹配定位按钮）
      return await this.fetchCommentsViaModal(topic);
    } catch (error) {
      logError(`获取帖子评论失败: ${topicId}`, error);
      return null;
    }
  }

  /**
   * 通过文本内容在页面中定位目标 topic 对应的"查看详情"按钮
   */
  private async findButtonByText(topic: Topic): Promise<import('playwright').ElementHandle | null> {
    if (!this.page) return null;

    // 提取文本片段用于匹配
    const text = topic.talk?.text || topic.question?.text || topic.answer?.text || '';
    if (!text) {
      log(`帖子 ${topic.topic_id} 无文本内容，无法通过文本匹配`);
      return null;
    }

    // 取前 30 个字符作为匹配片段，去除换行
    const snippet = text.replace(/\n/g, ' ').substring(0, 30);
    log(`文本匹配片段: "${snippet}"`);

    // 在页面中查找包含该文本的 app-topic 元素索引
    const matchIndex = await this.page.evaluate((searchText: string) => {
      // @ts-expect-error - document is available in browser context
      const topics = document.querySelectorAll('app-topic');
      for (let i = 0; i < topics.length; i++) {
        const content = topics[i].textContent || '';
        if (content.includes(searchText)) {
          return i;
        }
      }
      return -1;
    }, snippet);

    if (matchIndex === -1) {
      log(`未在页面中找到匹配文本的 app-topic 元素`);
      return null;
    }

    log(`文本匹配成功，app-topic 索引: ${matchIndex}`);

    // 在匹配的 app-topic 内查找"查看详情"按钮
    const button = await this.page.evaluateHandle((idx: number) => {
      // @ts-expect-error - document is available in browser context
      const topics = document.querySelectorAll('app-topic');
      const target = topics[idx];
      if (!target) return null;
      return target.querySelector('div.details-container .text');
    }, matchIndex);

    const element = button.asElement();
    if (!element) {
      log(`匹配的 app-topic 内未找到"查看详情"按钮`);
      return null;
    }

    return element;
  }

  /**
   * 模态框方案：通过文本匹配定位按钮，点击打开模态框获取评论
   */
  private async fetchCommentsViaModal(topic: Topic): Promise<Comment[] | null> {
    if (!this.page) return null;

    const button = await this.findButtonByText(topic);
    if (!button) {
      return null;
    }

    // 检查按钮是否可见
    const isVisible = await button.isVisible().catch(() => false);
    if (!isVisible) {
      log('匹配到的按钮不可见');
      return null;
    }

    const result = await this.tryClickDetailButton(button, topic.topic_id, -1);
    // tryClickDetailButton 返回 undefined 表示不匹配（理论上不应发生）
    return result !== undefined ? result : null;
  }

  /**
   * 尝试点击一个"查看详情"按钮，打开模态框后从 HTML 解析评论
   * @returns Comment[] | null 成功时返回评论，undefined 表示模态框未出现
   */
  private async tryClickDetailButton(
    button: import('playwright').ElementHandle,
    topicId: string,
    buttonIndex: number
  ): Promise<Comment[] | null | undefined> {
    if (!this.page) return undefined;

    // 滚动按钮到可视区域并点击
    await button.scrollIntoViewIfNeeded();
    await randomDelay(300, 500);
    log(`点击"查看详情"按钮 (topicId: ${topicId})`);
    await button.click();

    // 等待模态框出现
    try {
      await this.page.waitForSelector('div.topic-detail', { timeout: 5000 });
    } catch {
      log(`按钮 #${buttonIndex}: 点击后模态框未出现，跳过`);
      return undefined;
    }

    // 等待评论内容渲染
    await randomDelay(1500, 2500);

    log(`按钮 #${buttonIndex}: 模态框已打开，开始滚动加载全部评论...`);

    // 在模态框内滚动加载全部评论
    await this.scrollModalForAllComments();

    // 从 HTML 解析评论
    const comments = await parseCommentsFromHTML(this.page);

    // 关闭模态框
    await this.closeModal();

    if (comments.length > 0) {
      log(`获取到 ${comments.length} 条完整评论`);
    } else {
      log(`帖子无评论: ${topicId}`);
    }

    return comments;  // 返回空数组也是成功（帖子无评论）
  }

  /**
   * 在模态框内滚动加载全部评论（基于 DOM 元素数量判断）
   */
  private async scrollModalForAllComments(): Promise<void> {
    if (!this.page) return;

    let noNewCount = 0;
    let lastCount = 0;
    let scrollCount = 0;

    // 获取初始评论数量
    lastCount = await this.page.evaluate(() => {
      // @ts-expect-error - document is available in browser context
      return document.querySelectorAll('.comment-container').length;
    });

    while (noNewCount < 2 && scrollCount < 30) {
      // 在模态框内滚动到底部
      await this.page.evaluate(() => {
        // @ts-expect-error - document is available in browser context
        const modal = document.querySelector('div.topic-detail');
        if (modal) {
          modal.scrollTop = modal.scrollHeight;
        }
      });

      scrollCount++;
      await randomDelay(1500, 2500);

      const currentCount = await this.page.evaluate(() => {
        // @ts-expect-error - document is available in browser context
        return document.querySelectorAll('.comment-container').length;
      });

      if (currentCount === lastCount) {
        noNewCount++;
      } else {
        noNewCount = 0;
        lastCount = currentCount;
        log(`  模态框滚动 #${scrollCount}: DOM 中 ${currentCount} 条评论`);
      }
    }
  }

  /**
   * 关闭模态框（点击遮罩区域）
   */
  private async closeModal(): Promise<void> {
    if (!this.page) return;

    try {
      // Escape 不工作，直接点击遮罩区域关闭
      await this.page.click('div.topic-detail', {
        position: { x: 100, y: 400 },
      });
      // 等待模态框从 DOM 中移除
      await this.page.waitForSelector('div.topic-detail', {
        state: 'detached',
        timeout: 3000,
      });
      await randomDelay(500, 800);
    } catch (error) {
      logError('关闭模态框失败', error);
    }
  }

  /**
   * 关闭浏览器
   */
  async close(): Promise<void> {
    if (this.context) {
      await this.context.close();
      log('浏览器已关闭');
    }
  }

  /**
   * 主要的抓取方法（增量模式）
   */
  async scrape(): Promise<Topic[]> {
    try {
      await this.init();
      await this.navigateToGroup();
      return await this.loadLatestTopics(20);
    } catch (error) {
      logError('抓取失败', error);
      throw error;
    }
  }
}
