---
unit_type: article
article_id: "lbs7ewna2t6n"
topic_id: 82255514454848412
title: "给大家汇报一下最近的工作"
source_locator: "sqlite://xz.db/articles/lbs7ewna2t6n"
local_path: "articles/lbs7ewna2t6n.html"
extraction_status: "ok"
content_hash: "5ef16d86cb7b2d334828f2587052d5acd37618a43741a1aa9f6cfefa70f0ec9b"
generated_at: "2026-05-09T14:31:52+08:00"
---

# Article lbs7ewna2t6n: 给大家汇报一下最近的工作

## Coverage

- Parent topic: [[82255514454848412]]
- Read status: source_cache_created
- Extracted characters: 6735
- High-value signals: 期权, 肥尾, 波动率, 组合, 对冲, 美股

## Detailed Notes

- [肥尾, option, 肥尾, tail, 尾部] FatTail Butterfly 能获强烈的正期望是在概率分布上非常聪明的“趋利避害”了，在尖峰部分做了Short Straddle在肥尾部分买了超量的Long Options 所以活该套利。
- [组合, 对冲, tail, 对冲, 组合] 这里我们就能发现一个构造良好的FatTail ButterFly 为什么被塔勒布在《动态对冲》里被推崇了，因为这个组合的构造在这个分布上完美的“趋利避害”了。
- [肥尾, 肥尾, tail, 尾部, AI] 而肥尾部分，这里没能画全，一个FatTail ButterFly，在肥尾的部分是反而有收益的。
- [期权, 组合, 期权, 组合, 概率] 原理就是用期权到期收益分布的模拟乘以中间的概率分布图变成的函数PDF，乘之后的结果就是这个组合的期望收益了。
- [期权, 肥尾, 期权, 肥尾, 市场] 所以Skew最后这样子的原因是市场明白肥尾分布是真实存在的，并且在流行的BSM语言下大家将就就这样描述好了，因为并没有一个被普遍接受的基于肥尾分布的期权模型。
- [肥尾, put, call, 肥尾, 执行价] 这里解释一下所谓肥尾超配的 ButterFly，无非是一个标准的ButterFly，比如卖10张Put和Call之后，再买10张的Put和Call在不同的执行价和到期日上。
- [肥尾, 肥尾, tail, 市场, AI] 可计算的结果明晃晃的就在这里，根据真实的分布PDF和FatTail Butterfly 收益分布乘积之后的结果就是一个正期望占满视野的图，是市场对尖峰肥尾的估计估计不足到如此程度吗？
- [期权, 组合, 期权, 组合] 但因为期权组合的PnL其实受诸多因素影响，这个模拟也只能是个大概。
- [期权, 组合, 期权, 组合] 最下面一张图是这个工具的核心功能，计算一个期权组合在真实分布情况下的期望收益。
- [期权, 期权, 交易, AI] 最近在整理重构自己的期权交易的思路，并配合AI Agent的编程新范式给自己开发对应的工具。

## Traceability

- article_id: `lbs7ewna2t6n`
- topic_id: `82255514454848412`
- local_path: `articles/lbs7ewna2t6n.html`
- source status: `ok`

## Open Questions

- None from article cache generation.