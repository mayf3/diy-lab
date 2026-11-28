# Christmas Buddy V1 · Lean 形式化证明（首批）

- 上游方法：`mayf3/primitives@67212e4` MODEL_CENTERED_DEVELOPMENT v0.1.0（固定提交采用，不复制上游仓库）。
- 工具链：`leanprover/lean4:v4.19.0`（与 primitives 固定版一致），无 Mathlib，纯核心库。
- 复现：`python3 source-data/christmas-buddy/proof/verify_proof.py`
  （= `lake build` + `lake env lean Axioms.lean` 公理审计 → `verification.json`）。
- 公理白名单：`propext, Classical.choice, Quot.sound`；`sorryAx` 直接 FAIL。
- 最近验证：见 `verification.json`（2026-11-28，23 定理全 PASS，0 违规）。

## 证据三层纪律（governance CTR-MGD-007）

| 层 | 本轮覆盖 | 状态 |
|---|---|---|
| 模型内证明 | M1/M2/M5 的 23 个定理（本目录） | **PROVEN**（模型内） |
| 实现符合模型 | 见 MAP 列——多数实现尚未存在（固件/EDA 工程） | **NOT_YET**，下轮任务 |
| 真实环境验收 | 无（未通电、未打样） | **NOT_YET** |

模型证明通过**不**证明代码正确，更不证明实物工作。三层不可互相替代。

## 模型与定理清单

| 模型 | 文件 | 性质/定理 | 说明 |
|---|---|---|---|
| M2 设备状态机 | `src/ChristmasBuddy/StateMachine.lean` | thm_sleep_priority | K4 晚安在**所有**状态转移到 Goodnight（最高优先） |
| | | thm_goodnight_silent | 晚安态扬声器关闭 |
| | | thm_no_audio_conflict | 无任何状态麦克风与扬声器同时开启（I2S 资源互斥） |
| | | thm_goodnight_terminal | 晚安态只能被 wake 拉出（含 fatal 不可打断） |
| | | thm_fatal_not_goodnight | 非 Goodnight 状态 fatal → Error（故障可表达） |
| | | thm_error_recoverable | Error + reset → Idle（可恢复） |
| | | thm_return_home_*（6 条） | 每个状态有到达 Idle 的 witness 路径（进展性） |
| | | thm_wake_returns_idle_safe | 唤醒后扬声器保持关闭 |
| M1 电源 | `src/ChristmasBuddy/Power.lean` | thm_magic_within_adapter | 常规最坏（Magic 并发）×1.5 ≤ 3A 适配器 |
| | | thm_worst_within_adapter | 设计最坏并发 ≤ 3A（余量为 0，由 M2 帽策略兜底） |
| | | thm_led_capped_rail | LED 软帽 60% 后 ≤ LED 轨 1.6A |
| | | thm_led_rail_covers_uncapped | 不设帽的最坏也被轨容量覆盖（硬件兜底） |
| | | thm_rail_sum_bound | 通用引理：分域不超 ⇒ 总和不超 |
| | | thm_3v3_rail | ESP32 峰值 + mic + 杂项 ≤ 3V3 轨 500mA |
| | | thm_pi_measured_peak_obligation | 显式登记的未证义务（实测轮解除） |
| M5 制造版本 | `src/ChristmasBuddy/Version.lean` | thm_frozen_are_complete | frozen 清单中的发布四段齐全 |
| | | thm_incomplete_never_manufacturable | 四段不齐 ⇒ 永不可制造（安全门禁） |
| | | thm_frozen_manufacturable | frozen 发布可进入制造流程 |
| | | thm_complete_sound | complete 判定与逐段 isSome 合取等价 |

## 环境假设（ASM，模型外，责任边界）

- ASM-1：K4 事件总能送达状态机（方案 A：ESP32 硬件路径；Pi 死机仍可达）。→ 实物测试轮验证。
- ASM-2：Idle 态 `repeatReq` 时刻存在可重播回答。→ 固件实现保证（MAP 未落地）。
- ASM-3：云超时被运行时包装为 `cloudFail`。→ 固件实现保证。
- ASM-P1：适配器为合规 5V/3A 认证电源。→ 采购轮核对铭牌。
- ASM-P2：budget.json 模块电流取数据手册最大值或保守估计。→ 下单轮复核数据手册。

## UNPROVEN 义务（显式登记，不冒充已证）

- OB-1：制造文件（Gerber/坐标/BOM）确实来自已批准 PCB 版本——待真实 EDA 工程产出，
  由 `../m5_manifest.py` 哈希绑定 + 实测核对。Lean 只证结构规则（四段齐全才可制造）。
- OB-2：Pi 实测峰值 ≤ 520mA 预算——实测轮解除。
- OB-3：实现映射（MAP）未落地：固件、EDA 工程均不存在，本批定理对实现**无约束力**，
  只有实现出现并完成 MAP 后才进入「实现符合模型」证据层。

## 与 Space Buddy R1 的编号差异

Space Buddy R1 的 M1–M4 是（电气连接/机械结构/制造状态机/视觉）；本项目任务书定义
M1–M5 为（电源/设备状态机/机械装配/视觉约束/制造模型）。两者同构但编号不同，
阅读 PR 与工作台记录时须按各自项目页解释，不得混用编号。
