# Christmas Buddy V1 工程预研报告（主报告）

日期：2026-11-28｜分支：feat/christmas-buddy-v1-preresearch（基于 origin/main@370786b）
作者：Agent（mayf3）｜状态：**预研完成，未下单、未采购、未打样、未通电**

---

## 一、仓库现状审计（deliverable A）

### 1.1 三仓库真实状态

| 仓库 | 分支/HEAD | 关键事实 |
|---|---|---|
| mayf3/diy-lab | 主目录在 feat/recorder-v1-buildkit（PR #27 未合）；本 PR 基于 origin/main | 5 个项目；无任何 STL/STEP 入库；EDA 相关内容在未合并分支 |
| mayf3/primitives | main@67212e4（本地）；**四个工程规范文件只在远端分支** feat/model-engineering-toolchain-v1 等，未合 main | MODEL_CENTERED_DEVELOPMENT v0.1.0 已入 main；Lean 4.19.0 固定；verify_lean.py 公理审计可复用 |
| mayf3/agent-development-governance | main@403cba3（2.0.0-rc.5） | Model-Code Conformance 由 AGENT_MODEL_GUIDED_DEVELOPMENT_V1 承载（CTR-MGD-005/006/007）；无硬件专属规范 |

### 1.2 PR 谱系（防止把历史计划当实现）

- **PR #23/#24（OPEN）**：Magic Tent 真实卧室版。**A12**=KURA 低床+蚊帐现场约束（停止森林展示板路线）；
  **A13**=床外电子互动（投射灯/控制盒/PIR）**planned+HOLD、未采购**。→ Christmas Buddy 正是把
  "圣诞 AI 互动"从床架场景解耦出来的独立产品（Free 底座），与 A12/A13 决策一致且不冲突。
- **PR #28（OPEN，codex/eda-pcba-setup-20261126）**：嘉立创 EDA 工具链**已安装激活、MCP 握手与编辑器往返实测通过**（2026-11-26）；
  硬件工作台 workbench/（serve.py:8135）。但**真实 EDA 工程/原理图/PCB/制造文件一概不存在**——"EDA 环境可用 ≠ 产品 PCB 存在"。
- **PR #29（OPEN，feat/space-buddy-r1）**：Space Buddy Deck R1（2×2 按键 USB HID）已建立
  **M1–M4 建模先例、G0–G8 门禁、版本四元组 R1.pcb.cad.fw.bom、任务书格式**。外壳 CAD 完成（6 件 STEP+检查全绿），
  PCB 未开始。→ Christmas Buddy 显式继承其方法论；**M 编号体系不同**（本项目 M1–M5=电源/状态机/机械/视觉/制造，
  Space Buddy M1–M4=电气/机械/制造状态机/视觉），阅读时按各自项目页解释。
- **PR #30（OPEN，feat/governance-adoption）**：治理采用记录。其「Lean=计划中暂缓」的触发条件
  （载板布线复杂化或制造协作方介入）**被本任务的用户指令显式触发**——本项目交付了首批 Lean 定理。
- ⚠ 并行会话：diy-lab 主目录有未跟踪文件（gt-*.html、kura-v1/、tree-v2/）；diy-lab-pcba 工作树有
  2026-11-28 的未提交改动（Hardware Studio 审计等）。**本 PR 不触碰、不提交、不回退它们**（AGENTS.md 规则 10）。

### 1.3 能力盘点

**可复用**：静态生成器+check.py 门禁体系；DOAVR 双视图；Blender/CadQuery/Lean 本机工具链；
嘉立创 EDA CLI（本机可用）；Space Buddy 的 M 建模/四元组/任务书先例；Magic Tent 的 BOM/采购纪律。

**缺失（本轮补齐或登记）**：电源预算模型（✅ 已建）、网表级原理图（✅ 已建）、机械-电子联合检查（✅ 已建）、
视觉机器检查（✅ 已建）、Lean 硬件证明（✅ 首批 23 定理）、任务书生成器（✅ 已建）、
EDA 客户端内真实工程（⏳ 下一阶段）、C 编号数据库（⏳ 下单轮）、制造包生成器（⏳ G7 前）。

---

## 二、A–M 交付物状态总表

状态口径（governance 三层证据纪律）：**文档设计 ≠ CAD 完成 ≠ 仿真/检查通过 ≠ DRC 通过 ≠ 实物打样 ≠ 实物测试 ≠ 验收**。下表"状态"列最高只到其真实层级。

| 项 | 交付物 | 状态 | 层级 | 证据 |
|---|---|---|---|---|
| A | 仓库现状审计 | **PASS** | 文档 | 本报告 §一 |
| B | 嘉立创 EDA 工作流研究报告 | **PASS** | 文档+本机实测 | reports/01-jlc-eda-workflow.md；eda/environment-status.json |
| C | 两套电子架构比较 | **PASS（推荐 A）** | 文档（决策待用户） | architecture/architecture.md（A=4.15 vs B=3.43） |
| D | 初版原理图 | **PASS（网表级）** | 网表+ERC 通过；EDA 客户端工程=DRC 未跑 | eda/netlist.json；erc_report.md（0 错误） |
| E | 初版机械模型 | **PASS（CAD 完成）** | 参数模型+STEP/STL 导出；未试打印 | mech/outputs/（两案 6+ 件 STEP/STL） |
| F | 两套视觉方案 | **PASS（渲染完成）** | 真实模型渲染 8 视图×2 案；盲评未执行 | renders_local/christmas-buddy/；visual/visual-specs.json（12/12） |
| G | PCB×外壳装配验证 | **PASS（几何检查）** | CadQuery 布尔求交 20/20；PCB 仅 58×66 假想板，布局后需复检 | mech/assembly_check.json |
| H | BOM 与数据手册 | **PASS（文档级）** | 29 项 BOM 全 CHECK/HOLD；关键 datasheet 链接已核验；C 编号未核 | bom.csv；references |
| I | 电源预算与接口定义 | **PASS（计算+检查通过）** | 6/6 门禁；76 引脚接口表 | power/budget.json；interfaces/interfaces.json |
| J | 数学模型设计 | **PASS** | M1–M5 模型+Python 实现 | proof/README.md；各目录脚本 |
| K | Lean 证明（首批） | **PASS（模型内证明）** | 23 定理 lake build PASS+公理审计干净；**对实现无约束力（MAP 未落地）** | proof/verification.json |
| L | 工作台集成方案 | **PASS（文档+MVP）** | reports/03-workbench-integration.md；catalog 条目待 PR #28 合并后补 | — |
| M | 完整工程任务书 | **PASS（文档级）** | 14 任务全要素；需求追踪 0 悬空；门禁负责人合规 | tasks/christmas-buddy-v1.tasks.json |

**明确未达成/待验证（不冒充）**：
- DRC/DFM：**UNKNOWN**（未在 EDA 客户端执行——任务 T-SCH/T-PCB）。
- 元件 C 编号/现价/库存：**UNKNOWN**（下单轮逐项核实）。
- 试打印公差（0.2mm 假设）：**UNKNOWN**（T-MEC 试打印）。
- 云链路时延 p50≤3s：**UNKNOWN**（预研判断为可行，实测轮判定）。
- Pi 实测峰值 ≤520mA：**UNPROVEN 义务**（Lean 中显式登记）。
- 审美达标：**不可证明**（盲评+人工验收承担）。

---

## 三、决策摘要（按任务书要求的 9 问）

**1. 推荐哪套电子架构？**
方案 A（Pi Zero 2 W + ESP32-S3 协处理器），加权 4.15 vs 3.43。决定性理由不是成本（A 只贵约 ¥25），
而是**儿童产品的失效安全**：K4 晚安强制静音走 ESP32→2N7002→功放 SD 的硬件路径，Pi 死机/重启时
眼睛仍受控；LED 时序由 RMT 专用外设承担，Linux 只做云交互。B 案保留为降级路径（U3 不贴+焊桥切换，
触发条件见 architecture.md），**最终选择须用户签字（A05）**。

**2. 第一块 PCB 应该做多大？**
58×66×1.6mm 双面（standing 在 XZ 平面）。由机械弦长检查反推：体部内腔 Ø74 级别下 58mm 板宽 +
Pi 65mm 迭放弦长全部通过（20/20）。外形冻结等试打印公差实测。

**3. 哪些模块集成，哪些独立？**
载板集成：电源链（PTC/TVS/buck）、功放、麦克风、LED 电平转换、按键、ESP32 模块（SMT 贴装）。
独立模块：Pi Zero 2 W（排母迭放，可换核）、眼/星灯模组（PH2.0 线缆，服务声学与装配）、喇叭（腔体件）、
树灯扩展（预留座）。不集成：电池、彩屏、USB 数据（隐私边界）。

**4. 机械结构是否已经可制造？**
**几何可制造已验证（20/20 检查），工艺可制造未验证**——0.2mm 打印公差是假设，螺丝柱/加强筋未细化，
试打印是硬前置（T-MEC）。不能凭渲染图判断"能打印"。

**5. 视觉效果是否达标？**
机器可检查约束 12/12 通过、两案真实渲染完成；**审美达标只能由盲评+人工验收判定**，
脚本不证明"好看"（M4 模型的边界声明）。

**6. 嘉立创能否直接制造？**
流程上能（EDA CLI/DRC/制造输出 API 本机实测可用；SMT 双面贴片支持），但**当前没有任何可下单文件**——
原理图未进客户端、C 编号未核、外形未冻结。按门禁，报价批准（T-GATE）前不产生订单。

**7. 哪些性质已被形式化证明？**
23 条（Lean 4.19，公理白名单内，模型内 PROVEN）：晚安最高优先/晚安静音/音频互斥/晚安仅可被 wake 打断/
故障可表达且不打断晚安/错误可恢复/六状态进展性 witness/唤醒安全/电源 5 条预算定理/分域求和引理/
3V3 轨容量/版本四元组 4 条门禁。**边界**：它们是模型的性质；实现映射（MAP）未落地前对固件无约束力。

**8. 哪些仍然只是工程假设？**
Pi 峰值 520mA、buck 效率 0.85、打印公差 0.2mm、扬声器 4Ω/3W 选型、时延 p50≤3s、云 API 可用性、
嘉立创 SMT 对 ESP32 模块贴装良率、适配器 3A 认证。全部在 BOM/proof/ASM 中显式登记，实测轮解除。

**9. 下一步最值得投入的三件事？**
1. **架构与外观双决策**（用户签字 A05 + 盲评）——解锁全部下游，零成本高杠杆。
2. **EDA 客户端建图 + PCB 布局**（T-SCH/T-PCB）——把网表变成真工程，DRC+STEP 联检闭合 OB-1。
3. **试打印 + 公差实测**（T-MEC）——0.2mm 假设是机械冻结的唯一阻塞，一天内可完成。

---

## 四、证据文件索引

| 类别 | 文件 |
|---|---|
| 电源 | power/budget.{json,md}、power_budget.py |
| 接口 | interfaces/interfaces.{json,md}、interfaces.py |
| 架构 | architecture/architecture.{json,md}、architecture.py |
| 网表/EDA | eda/netlist.json、erc_report.md、environment-status.json、netlist.py |
| BOM | bom.csv（29 项） |
| 机械 | mech/params.py、build_mech.py、assembly_check.{json,md}、outputs/（STEP+STL） |
| 视觉 | visual/visual-specs.{json,md}、render_blender.py、renders_local/ + public/media/ |
| 证明 | proof/src/*.lean、verification.json、README.md、verify_proof.py |
| 制造追溯 | m5_manifest.py、m5_manifest.json |
| 任务书 | tasks/product-spec.json、christmas-buddy-v1.tasks.json、traceability.md、scripts/gen_eng_tasks.py |
| 集成 | reports/03-workbench-integration.md |
| EDA 研究 | reports/01-jlc-eda-workflow.md |
