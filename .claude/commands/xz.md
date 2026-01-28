/xz N (= full N) | update | help 下载许哲知识星球

如果用户输入的参数是 `help`，则显示以下帮助信息（直接输出文本，不运行命令）：

```
/xz           增量更新（最新20条）
/xz full      全量下载
/xz full N    全量下载，每次N个
/xz N         同 full N
/xz open      打开浏览器（不退出）
/xz help      显示帮助
```

否则根据用户输入的参数，运行对应的命令：

- `/xz` 或 `/xz update` → `npx tsx src/index.ts`
- `/xz full` → `npx tsx src/index.ts --mode=full`
- `/xz full N` → `npx tsx src/index.ts --mode=full --limit=N`
- `/xz N`（纯数字）→ `npx tsx src/index.ts --mode=full --limit=N`
- `/xz open` → `npx tsx src/index.ts --mode=open`

工作目录：/Users/tony/dev/personal/xz
