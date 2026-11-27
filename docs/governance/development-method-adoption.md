# DIY Lab · 研发方法（数学建模 / Lean / 治理）采用记录

**采用日期：2026-11-27 · 维护人：Maker Lab 本地 Agent · 状态：已采用，按 PR 逐项落地**

## 一、采用的上游与精确提交

| 上游 | 精确提交 | 内容 | 用途 |
| --- | --- | --- | --- |
| [mayf3/primitives](https://github.com/mayf3/primitives) | `67212e487e7e0c5040ba866b51a9de99bf6a0ecb`（2026-11-27） | MODEL_CENTERED_DEVELOPMENT v0.1.0、MODEL_GUIDED_DEVELOPMENT v0.1.0、MODEL_FEEDBACK（2026-11-20）、LEAN.md（0.6.1）、domains/agent-workflow/FORMALIZATION（0.3.1） | 数学建模方法、Lean 目录与验证规则、反例闭环 |
| [mayf3/agent-development-governance](https://github.com/mayf3/agent-development-governance) | `403cba321dd309410043f42a35807533e3660387`（VERSION 2.0.0-rc.5） | AGENTS.md、.agents/README.md、SPEC_GOVERNANCE_V1.0.0、spec-governance skill | 采用判定、三轴路由（Authority/Plan/Assurance）、证据责任 |

两个上游均为**固定提交采用**（非 main 漂移引用）。上游更新不会自动改变本项目；
每次更新需按 §三 重新评估并更新本文件。

## 二、采用状态与适用范围

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 方法规范阅读与建模判断 | **已采用** | 行为变更前按 MODEL_GUIDED_DEVELOPMENT §1 判断：已有模型复用 / 补足 / 不适用 |
| 数学模型实例 | **部分采用** | Space Buddy R1 的 M1–M4 见 `source-data/agent-button-deck/pcba-v1/models-r1.md`（电气/机械/制造状态/视觉 + 跨版本一致性约束） |
| Lean 形式化 | **计划中，暂缓** | 优先级：M3 制造状态机合法性、跨版本四元组一致性；当前规模下先以检查表 + EDA 报告 + 工作台测试承担，触发条件=载板布线复杂化或制造协作方介入 |
| 开发治理（PREFLIGHT/路由/证据） | **部分采用** | PR 划分（A/B/C）、三轴路由思想、证据分层已应用；暂未引入 governance.lock/工具链完整落地 |

**不采用/不复制**：不把 primitives/governance 整套仓库复制进 diy-lab；不把共享证明
或业务状态迁入本项目；本项目只保留需求权威、模型实例（M1–M4）、实现映射与真实验收。

## 三、版本更新与重新验收方式

1. 上游任一仓库 main 推进 → 本文件不自动变化。
2. 需要上游新能力或收到模型挑战（Model Challenge Issue）时：clone 精确新提交，
   按 consumer-local impact assessment 评估受影响的模型/前提/验收，逐项判定
   MIGRATE / RETAIN / TEMPORARY_BRIDGE。
3. 评估结论写入本文件的「上游更新记录」小节（含新 commit、影响、重新验收 PR）。
4. 重新验收 = 重跑受影响项目的检查/测试 + 按原验收标准复核对应实物/工作台呈现。

## 四、本项目模型实例索引

| 模型 | 位置 | 状态 |
| --- | --- | --- |
| M1–M4（Space Buddy R1） | `source-data/agent-button-deck/pcba-v1/models-r1.md` | 文档化；Lean 暂缓（触发条件见上） |
| 录制器三态冻结/状态合同 | `docs/eda/environment-status.json` + workbench 状态合同 | 已实现并有测试 |
| 亲子记录器取景模拟 | `source-data/parent-child-recorder/framing_sim.py`（13 项自检） | simulation 证据 |

## 五、证据纪律（引用 primitives MODEL_CENTERED_DEVELOPMENT §7）

模型/证明、实现对应、原任务验收三层证据不可互相替代；所有结论绑定精确版本、
范围与执行证据；未知保持未知。嘉立创 EDA 的「editor_round_trip passed」只证明
编辑器读写能力，不代表电路正确或产品可制造。
