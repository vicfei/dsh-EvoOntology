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
