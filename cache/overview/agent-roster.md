# XZ Reading Agent Roster

Generated: 2026-05-09 14:25

## Shard Assignment

| Shard | Rule | Agent | Agent ID | Write scope |
| ---: | --- | --- | --- | --- |
| 0 | `topic_id % 5 == 0` | McClintock | `019e0b69-4828-72a2-9489-37018ff631f7` | `details/topics/`, `details/ledgers/shard-0.*` |
| 1 | `topic_id % 5 == 1` | Herschel | `019e0b69-5137-76f3-a001-8a847cdf8e33` | `details/topics/`, `details/ledgers/shard-1.*` |
| 2 | `topic_id % 5 == 2` | Dalton | `019e0b69-5a26-76d0-bdf1-24eda25e0730` | `details/topics/`, `details/ledgers/shard-2.*` |
| 3 | `topic_id % 5 == 3` | Banach | `019e0b69-631a-7e71-ac94-1b1483c84764` | `details/topics/`, `details/ledgers/shard-3.*` |
| 4 | `topic_id % 5 == 4` | Volta | `019e0b69-6cb2-7420-a2f9-cc400a846b7a` | `details/topics/`, `details/ledgers/shard-4.*` |

## Coordinator Rule

The main agent only coordinates, merges, and verifies. Reading agents own deep reading for their shard and should not write shared overview files except their shard summaries.
