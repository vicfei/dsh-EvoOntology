# dsh-EvoOntology — DeepSeek Harness 的自演化本体层

**一个每条记录都带证据的演化引擎：轨迹进、假设轮出、评估不赢不发布。
第一相位驱动家族自己的 agent，同一引擎长成完整的文档/数据本体层。**

[![npm](https://img.shields.io/npm/v/dsh-evoontology)](https://www.npmjs.com/package/dsh-evoontology) [![License: MIT](https://img.shields.io/badge/license-MIT-3da639)](LICENSE)

> 结构致敬 [ruc-datalab/EvoOntology](https://github.com/ruc-datalab/EvoOntology)（1.3k★，MIT，arXiv 2609.15779）
> ——净室实现，零上游代码，非官方无隶属。[English README](README.md)

## 一句话定位

agent 每次会话都在重学同样的东西。解法不是更大的上下文窗口，而是一个
**会记账、且只在证据说话时才改变的层**：

- **轨迹即语料**：agent 实际做过的事（决策/结果/引文）append-only 入证据库，永不改删；
- **假设轮+冻结预算**：每轮演化带正式假设与冻结预算，耗尽即 incomplete、扩展须显式确认——没有半夜的静默自我修改；
- **评估不赢不发布**：候选版本必须在评估适配器上赢过现任才能上位（可重跑、有种子、照数公布）；
- **记录必带证据**：五记录 schema（Term/Mapping/Relation/Constraint/Evidence）继承家族 evidence-linked 格式。

**路线**：E1 演化内核 → E2 家族三仓接入（通用性证明）→ E3 语义层全量（EvoOntology 完整概念的 DSH 原生形态）→ E4 生态。

**不做**：MCP 优先（typed-tools 是原生面）、追八种连接器、刷榜、与家族 dsh-WrenAI 抢问答位。

详见 [ROADMAP](ROADMAP.md)（开发走 issue→branch→PR，CI 门从第一天装齐）。

## E1 内核 + E2 首个适配器

E1（零 LLM 内核）已发布：五记录证据库、轨迹库、阈值触发、冻结预算下的假设轮、评估门、SQLite 语义层种子。

**E2 第一个适配器**——家族自己的 [dsh-auto-ontology](https://github.com/vicfei/dsh-auto-ontology) 接入：
它的 `ao-trajectory/0.1` 导出变成轨迹，一轮假设轮为“没有引文支撑其类型”的词条提出改型，
再由兄弟仓自己的 eval 判官裁决：

```bash
auto-ontology export ontologies/x.json > trajectory.ndjson     # 发生过什么
evoontology trajectory import --from trajectory.ndjson         # 按事件 id 幂等
evoontology adapt auto-ontology --from trajectory.ndjson       # 提议 → 判官 → 评估门
auto-ontology apply --proposals .evo/runs/<run>.proposals.json --actor agent:<名字>   # 带回去
```

五步：导入（幂等）→ 投影（纯函数，每条记录带引文**及其判官结论**；被否决的认证变成 Constraint）→
提议（模型读 TBox 与该词条全部引文，指出一个被某条引文明说的既有类型，否则返回 null；畸形提议在见判官前即丢弃）→
裁决（走 auto-ontology **自己的 eval CLI**，判官逻辑零重写）→ 一轮（对投影、过评估门；赢了才发布，
并写出 `runs/<run>.proposals.json` 供回写）。评估门新增第四项 `endorsed`（净背书占比）：层要赢得更被证据支撑。

**赢了不代表什么**：改型词条按定义从 −1 变 +1，只要有一条过判官的提议这轮就赢——实验在判官，不在算术。
尽量给提议者与判官指定两个不同模型（`--proposer-model` / `--judge-model`），运行记录两者。
