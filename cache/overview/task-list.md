# XZ Corpus Reading Task List

Generated: 2026-05-09 14:23

## Goal

Create an auditable reading plan before any deep reading. The final reading cache will be topic-first: every topic is the canonical container, and articles/files/comments are tracked as attached source units.

## Verified Corpus Counts

| Unit | Count |
| --- | ---: |
| Topics | 1203 |
| Q&A topics | 863 |
| Talk topics | 340 |
| Articles | 47 |
| Files | 18 |
| Comments | 3805 |

## Files To Process

| file_id | topic_id | name | planned handling |
| --- | ---: | --- | --- |
| 185448811255442 | 4845555888114288 | NYorker2002-blowingup.pdf | extract and triage; full-read if core/adjacent |
| 212581415222811 | 2852151554255281 | QQQAI 基金小结（Till 202506）.pdf | extract and triage; full-read if core/adjacent |
| 218885224244111 | 4848581484881848 | 政策牛市与2015年牛市的区别.pdf | extract and triage; full-read if core/adjacent |
| 415514888242148 | 22255855418114511 | For QQQAI Token Holder（2026.4.15）.pdf | extract and triage; full-read if core/adjacent |
| 415544511222148 | 45811545482288218 | taleb_The Regress of Uncertainty.pdf | extract and triage; full-read if core/adjacent |
| 418111812411228 | 2852454254428551 | QQQAI 认购操作指南.pdf | extract and triage; full-read if core/adjacent |
| 418415128415818 | 8855148448515412 | 秦制漫谈第三篇 v2.pdf | triage as history_or_culture_guess; skip only after confirming no investment/risk analogy |
| 418452811848258 | 4844218115584828 | 20240705山西证券货币流动性系列报告五：解构央行资产负债表.pdf | extract and triage; full-read if core/adjacent |
| 418525288412558 | 8852218421881212 | 用凸性从不确定性中受益.pptx | extract and triage; full-read if core/adjacent |
| 418525288841888 | 5125581458511184 | 2025-4-28 用凸性从不确定性中受益.m4a | register as skipped-audio unless transcript exists |
| 418825415158828 | 5121451828822444 | 1_金禾分析初稿(2).docx | extract and triage; full-read if core/adjacent |
| 418841584552188 | 5121524218481544 | 政策大礼包.pdf | extract and triage; full-read if core/adjacent |
| 581542554288554 | 2852224422158451 | 关于最近贸易战的看法.pdf | extract and triage; full-read if core/adjacent |
| 585125828481114 | 4842428454411828 | VIX-Decomposition-2025-08-01.pdf | extract and triage; full-read if core/adjacent |
| 812851215884442 | 14588242224852542 | QQQAI 2025年三季度小结 A.pdf | extract and triage; full-read if core/adjacent |
| 818521215421182 | 8855155552422812 | 专访经济学家陈志武.pdf | extract and triage; full-read if core/adjacent |
| 818522888212142 | 2855448512845211 | 秦制漫谈第二篇.pdf | triage as history_or_culture_guess; skip only after confirming no investment/risk analogy |
| 818851815441122 | 4848545151824588 | 【嬉笑创客】是什么推动了政策豹变？.pdf | extract and triage; full-read if core/adjacent |

## Classification Policy

- `core`: direct trading/investing method: convexity, options, QQQAI, VIX/volatility, LETF/TQQQ/SQQQ, fat-tail, portfolio construction, hedging, Greeks, drawdown, leverage.
- `adjacent`: investment philosophy, macro/market structure/risk relevant to trading.
- `low`: operations/admin or weakly related external report.
- `non-investment`: unrelated everyday/history/culture content after triage.
- `skip_audio`: audio only and no transcript.
- `history_or_culture_guess`: routing guess only; final skip requires triage.

## Read Status Definitions

- `unread`: not yet processed.
- `triage_read`: enough content read to classify relevance and route.
- `full_read`: investment-relevant content fully read and summarized.
- `embedded_in_parent`: source/comment content captured in the parent topic cache.
- `source_cache_created`: independent source cache created and linked.
- `duplicate_covered_by`: duplicate source covered by canonical unit.
- `skipped_with_reason`: skipped with explicit reason.
- `parse_failed`: extraction/read failed and must appear in audit.

## Agent Plan

- Coordinator: maintains manifest, assigns shards, merges ledgers, writes overview, performs verification.
- Topic owners: each topic has exactly one owner; owner signs off final topic cache coverage.
- Source specialists: handle files/articles extraction and source caches when needed.
- Comment scanner: triages all 3805 comments, escalates investment-relevant comments to topic owners.

Concrete agents will be assigned after Tony confirms this manifest policy and sample rows.

## Pre-Reading Gate

Before dispatching reading agents, confirm:

1. Classification policy.
2. Comment policy: triage all comments; full-read/escalate investment-relevant comments; do not full-read irrelevant comments beyond triage.
3. Read status definitions.
4. Counts and representative sample rows from the manifest.

## Post-Reading Verification

- Count check must match topics=1203, articles=47, files=18, comments=3805.
- No `unassigned`, `unread`, or unresolved `parse_failed` rows.
- Keyword audit for QQQAI, 凸性, 期权, VIX, LETF, 肥尾, Greeks, 组合, 杠杆, 回撤.
- Random spot checks against raw DB/files for each agent shard.
- All skips, parse failures, ambiguity, and manual follow-up items go into `overview/audit.md`.
