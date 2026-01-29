# Topic 获取方案（Python + Playwright）

## 技术栈
- Python 3
- Playwright for Python

## 文件结构
```
py/
  fetch_topics.py      # 主脚本
output/
  response/            # 保存的 JSON
    28888825825151_{timestamp}.json
```

## 流程
1. 启动浏览器（headless=False，需要登录）
2. 导航到 `https://wx.zsxq.com/group/28888825825151`
3. 等待用户手动登录（首次）
4. `page.on('response')` 监听网络响应
5. 匹配 `api.zsxq.com/v2/groups/28888825825151/topics?scope=all` 开头的 URL
6. 提取 JSON，保存为 `{groupid}_{current_timestamp}.json`
7. 滚动页面触发翻页，持续捕获
8. 用户按 **Ctrl+C** 退出

## 运行方式
```bash
cd py
pip install playwright
playwright install chromium
python fetch_topics.py
```

## 验证方式
1. 运行脚本，浏览器打开星球页面
2. 手动登录后滚动页面
3. 检查 `output/response/` 目录是否有新 JSON 文件生成
4. 验证 JSON 内容包含 topics 数据
