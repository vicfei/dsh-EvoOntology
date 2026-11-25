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
evoontology adapt auto-ontology --from trajectory.ndjson \
  --auto-ontology <兄弟仓 checkout> --proposer-model M --judge-model N   # 提议 → 判官 → 评估门
auto-ontology apply --proposals .evo/runs/<run>.proposals.json \
  --from ontologies/x.json --actor agent:evoontology-adapter              # 带回去
```

五步：导入（幂等）→ 投影（纯函数，每条记录带引文**及其判官结论**；被否决的认证变成 Constraint）→
提议（模型读 TBox 与该词条全部引文，指出一个被某条引文明说的既有类型，否则返回 null；畸形提议在见判官前即丢弃，带原因落盘）→
裁决（走 auto-ontology **自己的 eval CLI**，判官逻辑零重写）→ 一轮（候选 = 投影加上过判官的改型**及其认证将新增的约束**，即回写后会投影出的那一层；赢了才发布，
并写出 `runs/<run>.proposals.json` 供回写）。评估门新增第四项 `endorsed`（净背书占比）：层要赢得更被证据支撑。

**赢了不代表什么**：改型词条按定义从 −1 变 +1，只要有一条过判官的提议这轮就赢——实验在判官，不在算术。
尽量给提议者与判官指定两个不同模型（`--proposer-model` / `--judge-model`），运行记录两者。

**一条流，一次运行**：未变化的流不会自行再开一次运行——输掉的轮次已花掉预算，再试一轮是 `evolve extend --run <id> --extra N --note "原因"`，记在运行上；
流变了才是新问题。崩溃的运行以 `aborted` 连同原因关闭，永不悬挂为 `running`。每轮的判官输入与裁决行各存 `runs/<run>.judge/round-N/`。

### 首轮实测（2026-11-25，照数公布）

一条流、三次尝试，数字全部来自运行文件与控制台日志，证据发布在兄弟仓的
[`eval/live-round/`](https://github.com/vicfei/dsh-auto-ontology/tree/main/eval/live-round)。
流：家族 23 份公开 README 的一次构建，再折叠一次、认证两次——374 个事件，370 条引文里 226 条落地；
投影出 128 个词条、177 条关系、1 条约束，其中 47 个词条的类型没有引文支撑。开轮前评估门 2.9627。
提议者 `deepseek-chat`，判官 `deepseek-reasoner`。

| # | 运行 · 轮 | 提议（47 个词条） | 判官 | 结果 |
|---|---|---|---|---|
| 1 | `20261125-183646` · 无 | 8 条有效 · 39 条畸形 | 未到判官 | **崩溃**：适配器自己打印畸形列表时抛 `KeyError: 'from_type'`；运行事后以 `aborted` 关闭并记下原因 |
| 2 | `20261125-184149` · 第 1 轮 | 10 条有效 · 37 条畸形 | 0 落地 · 10 否 | **输**：2.9627 对 2.9627，未发布 |
| 3 | `20261125-184149` · 第 2 轮 | 13 条有效 · 34 条 null · 0 畸形 | 1 落地 · 12 否 | **赢**：2.9693 对 2.9627，发布 `layer_v1` |

第 2 次的 37 条畸形：19 条把提示词放在引文前的来源标签一起抄了进去，11 条编了个 TBox 之外的类型
（JSON 模式不允许裸 null，模型拿 `json_object` 顶替），7 条又提了现行类型。此后重写提示词（引文按 JSON 行给、null 写明），第 3 次 0 畸形。

**那次扩展不是人亲手做的**：第 2 次输掉后预算已用完（1/1），“一条流一次运行”规则两次拒绝了未扩展的重跑；
多出来的这一轮来自 `evolve extend --run 20261125-184149 --extra 1 --note "…"`，由 `agent:shanghai-window`
依负责人对这项工作的常设授权发出，运行记录里如实写着。内核把扩展称作“显式的人类动作”，这一次不是。三次尝试因此全部公开。

判官落地的唯一一条：`OAR: dsh_plugin → upstream_project`（“Open Agent Runtime，带 GitHub 链接，由适配器接入”）。

**回写实测**：`apply --proposals` 改型 1 个实体、跳过 12 条未落地的，重放为空操作；重新导出多出 2 个事件
（新断言 + 带判官与运行名的否决认证），幂等导入后投影里只剩一个 `OAR`，类型 `upstream_project`，已落地。
回写暴露了两处缺口：其一，发布的层比真实回写多算了 0.0012（2.9693 对 **2.9681**）——认证新增的一条约束当时不在候选里，
现已补上，并由 CI 断言“发布的层 = 回写后的投影”；其二，回写的断言没带判官名（`by: "judge"`），兄弟仓 0.3.0 修复。

**这一轮说明不了的**：23 条受判提议里只有 1 条真阳性，样本只有一条流；提议者被允许说 null 之后，47 个词条里有 34 个一无所获；
判官工作目录当时按运行而不是按轮分开，第 2 轮覆盖了第 1 轮的判官输入与裁决行（现已按轮分目录）。
