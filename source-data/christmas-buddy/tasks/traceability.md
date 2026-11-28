# Christmas Buddy V1 圣诞精灵机器人 · v1 工程任务书（生成于 2026-11-28）

目标：独立摆放在儿童床边的圣诞主题 AI 互动机器人；借本项目建立 DIY Lab 第一套 AI 硬件研发样板流程。

## 非目标

- 不集成锂电池（第一版外置 5V/3A）
- 不用彩色屏幕（表情只用 LED 矩阵眼）
- 不做本地大模型推理（AI 全部云端）
- 不固定到 KURA 床架（Free 底座）

## 任务列表

### T-ADT-1 [ADT] 仓库与能力审计

- 负责人：agent｜依赖：—｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；AGENTS.md / 审计报告
- 输出：现状审计报告
- 验收：三仓库审计完成，可复用/缺失/修复清单齐备（本轮已交付）
- 风险：审计遗漏并行会话改动——已核对工作树与 PR 列表
- 证据类型：REPORT

### T-ARC-1 [ARC] 电子架构冻结 **【门禁·须人批准】**

- 负责人：human｜依赖：T-ADT-1｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-ADT-1 输出
- 输出：架构决策记录（用户签字）
- 验收：用户在架构比较报告上明确选择 A 或 B（本 PR 提供比较与推荐）
- 风险：架构选择错误导致返工——以降级触发条件约束
- 证据类型：DECISION

### T-SCH-1 [SCH] 原理图与 EDA 工程

- 负责人：agent｜依赖：T-ARC-1｜覆盖需求：REQ-002、REQ-005、REQ-006、REQ-009、REQ-011、REQ-012
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-ARC-1 输出
- 输出：EDA 工程文件 + 网表导出 + ERC
- 验收：EDA 客户端工程存在；sch_Drc.check 通过；导出网表与本仓 netlist.json 语义一致
- 风险：引脚冲突/封装错误——DRC + 数据手册逐脚核对
- 证据类型：EDA_REPORT

### T-PCB-1 [PCB] PCB 布局布线与 DRC

- 负责人：agent｜依赖：T-SCH-1｜覆盖需求：REQ-007、REQ-012
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-SCH-1 输出
- 输出：PCB 工程 + DRC/DFM 报告 + STEP
- 验收：pcb_Drc.check 通过；3D STEP 导出并与机械模型联合检查
- 风险：双面板走线拥挤——外形与接口已按 58×66 预演
- 证据类型：EDA_REPORT

### T-MEC-1 [MEC] 机械细化与可打印性

- 负责人：agent｜依赖：T-PCB-1｜覆盖需求：REQ-001、REQ-003、REQ-004、REQ-008
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-PCB-1 输出
- 输出：外壳工程 + 装配检查 + STL/STEP
- 验收：可打印性检查（壁厚/悬撑/公差）通过；试打印切片完成
- 风险：打印公差超 0.2mm 假设——试打印先行
- 证据类型：CAD_CHECK

### T-ASM-1 [ASM] 联合装配验证

- 负责人：agent｜依赖：T-MEC-1｜覆盖需求：REQ-008、REQ-010
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-MEC-1 输出
- 输出：PCB×外壳布尔干涉报告
- 验收：布尔干涉 0 冲突；接插件插拔净空 ≥8mm；USB-C 可达
- 风险：线缆弯曲空间不足——已留 8mm 半径约束
- 证据类型：CAD_CHECK

### T-VIS-1 [VIS] 视觉渲染与盲评

- 负责人：shared｜依赖：T-ASM-1｜覆盖需求：REQ-004、REQ-013
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-ASM-1 输出
- 输出：8 视图渲染 ×2 案 + 盲评记录
- 验收：盲评按协议执行且记录在案；优胜方案用户确认
- 风险：盲评两案接近——合并优点再评
- 证据类型：RENDER+REVIEW

### T-MDL-1 [MDL] 数学模型与 Lean 证明

- 负责人：agent｜依赖：T-VIS-1｜覆盖需求：REQ-005、REQ-009、REQ-014
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-VIS-1 输出
- 输出：M1–M5 模型 + 验证回执
- 验收：verify_proof.py PASS（公理白名单内）；m5_manifest check PASS
- 风险：实现漂移——MAP 未落地前不得声称实现符合模型
- 证据类型：LEAN_PROOF

### T-FW-1 [FW] 固件（ESP32 + Pi 服务）

- 负责人：agent｜依赖：T-MDL-1｜覆盖需求：REQ-002、REQ-005、REQ-006
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-MDL-1 输出
- 输出：可运行固件 + 模型适配器测试
- 验收：状态机适配器测试（合法/非法轨迹 fixtures）全过；真实设备动作与模型一致
- 风险：Pi 音频与云链路时延不达标——流式管线为验收项
- 证据类型：TESTED

### T-GATE-1 [GATE] 制造门禁（人工批准） **【门禁·须人批准】**

- 负责人：human｜依赖：T-FW-1｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-FW-1 输出
- 输出：报价/数量/风险确认记录
- 验收：用户确认 SKU/数量/运费/风险（付款前人工门禁）
- 风险：汇率/涨价——下单前重核价格
- 证据类型：DECISION

### T-FAB-1 [FAB] 打样与 SMT 下单执行 **【门禁·须人批准】**

- 负责人：vendor｜依赖：T-GATE-1｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-GATE-1 输出
- 输出：制造文件包（哈希绑定）+ 订单回执
- 验收：嘉立创订单回执 + Gerber/坐标/BOM 哈希与 m5_manifest 绑定一致
- 风险：SMT 扩展库料缺货——备选料二选一已在 BOM 登记
- 证据类型：RECEIPT

### T-BLD-1 [BLD] 装配与首次通电 **【门禁·须人批准】**

- 负责人：human｜依赖：T-FAB-1｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-FAB-1 输出
- 输出：组装记录 + 首通电记录
- 验收：装配完成记录 + 首次通电观察（人执行，Agent 不得代替）
- 风险：首次通电异常——断电开关 + 分域 PTC 兜底
- 证据类型：OBSERVATION

### T-TST-1 [TST] 实物测试与验收

- 负责人：shared｜依赖：T-BLD-1｜覆盖需求：REQ-006、REQ-009、REQ-010、REQ-012
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-BLD-1 输出
- 输出：电源/音频/时延/安全实测报告
- 验收：电源实测 ≤ 预算；时延 p50/p95 达标或如实记录未达标；安全路径实测
- 风险：实测不达标——如实记录，不得以文档完成冒充实测通过
- 证据类型：MEASUREMENT

### T-DOC-1 [DOC] 教程与工作台归档

- 负责人：agent｜依赖：T-TST-1｜覆盖需求：—
- 输入：source-data/christmas-buddy/tasks/product-spec.json；前序任务 T-TST-1 输出
- 输出：项目页 + 视图 + BOM 状态推进
- 验收：check.py/build.py 通过；页面桌面+手机目检记录
- 风险：视图漂移——render_diy_ir.py 自动生成
- 证据类型：REPORT

## 需求追踪矩阵

| 需求 | 任务 |
|---|---|
| REQ-001 | T-MEC-1 |
| REQ-002 | T-SCH-1、T-FW-1 |
| REQ-003 | T-MEC-1 |
| REQ-004 | T-MEC-1、T-VIS-1 |
| REQ-005 | T-SCH-1、T-MDL-1、T-FW-1 |
| REQ-006 | T-SCH-1、T-FW-1、T-TST-1 |
| REQ-007 | T-PCB-1 |
| REQ-008 | T-MEC-1、T-ASM-1 |
| REQ-009 | T-SCH-1、T-MDL-1、T-TST-1 |
| REQ-010 | T-ASM-1、T-TST-1 |
| REQ-011 | T-SCH-1 |
| REQ-012 | T-SCH-1、T-PCB-1、T-TST-1 |
| REQ-013 | T-VIS-1 |
| REQ-014 | T-MDL-1 |

## 机器检查

- 需求悬空：无
- 门禁负责人违规：无
- 依赖线性一致：True

