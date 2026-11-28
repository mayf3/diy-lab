# christmas-buddy｜Agent 执行规范（机器工作流视图）

> **自动生成·规范草案，未代表真实执行。** 唯一规范源：source-data/christmas-buddy/workflow.json。源资料需在执行当天重新检索；不要将下列 planned 标记为 verified。

**D（目标）**：做出可制造、可装配、可测试的 Christmas Buddy V1 圣诞精灵 AI 机器人（120–160mm，LED 矩阵眼，2×2 按键，云 GPT 对话），并把它作为 DIY Lab 第一套 AI 硬件研发流程样板。

**受众约束**：面向没有焊接和 PCB 经验的新手；不预设拥有 Bambu P1S、电子工具或嘉立创账号。

**禁止误解为目标**：

- 第一版不集成锂电池（外置合规 5V/3A）
- 不用彩色屏幕（表情只用 LED 矩阵眼）
- 不做本地大模型推理（AI 全部云端）
- 不固定到 KURA 床架（Free 底座）
- 预研阶段不下单、不采购、不生产制造文件

## 启动协议

1. 读取当前用户的设备/预算/技能约束；**只问缺少且会改变实际方案的信息**。不要假设用户有 P1S 或 Mac。
2. 自行获取官方上游、工程文件、BOM 和适用的软件版本；对上游每一个关键型号/版本记录来源、时间、可验证范围。
3. 可用工具能读到的页面、CAD/模型、硬件规格和报价，**自己调用工具检查**，不要把“去看源码”转交给用户。工具受限时请求最低限度文件，不编造已检查。
4. 报告每一关的状态：planned / observed / failed / blocked，输出证据位置、影响以及下一步。**模拟 ≠ 实物、读取 ≠ 验收、建议 ≠ 批准付款。**
5. 对付款、首次通电、不可逆烧录/焊接、儿童使用和安全相关动作，要求真实用户决定或现场证据；不绕过安全检查。

## O（资源选择和替代路线）

| 先看条件 | 你可以选什么 | AI 应如何分流 |
| --- | --- | --- |
| PCB/贴片/外壳如何制造？ | 嘉立创 EDA 打样 + SMT 贴片 + P1S 自印外壳（主路线） / 嘉立创代打印外壳（P1S 不可用时） / 面包板/模块搭验证机（架构风险高时） / 尚未决定 | Agent 完成设计与文件，人批准报价并付款，供应商制造；预研轮一律不下单 |

## 官方上游参考（执行时复核）

- 嘉立创EDA专业版 CLI 文档（查看 2026-11-28）：[来源](https://prodocs.lceda.cn/cn/api/guide/cli.html)
- 嘉立创EDA专业版 扩展 SDK（查看 2026-11-28）：[来源](https://github.com/easyeda/easyeda-api-sdk)
- MAX98357A 数据手册（查看 2026-11-28）：[来源](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf)
- SN74LVC1T45 数据手册（查看 2026-11-28）：[来源](https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf)
- TPS563201 数据手册（查看 2026-11-28）：[来源](https://www.ti.com/lit/ds/symlink/tps563201.pdf)
- ESP32-S3-WROOM-1 数据手册（查看 2026-11-28）：[来源](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1-u_datasheet_en.pdf)
- Christmas Magic Tent A12/A13（KURA 现场约束与床外电子暂缓）（查看 2026-11-28）：[来源](https://github.com/mayf3/diy-lab/pull/24)

## A/V/R（动作、证据、依赖与阻断）

### A01 · 三仓库现状审计（diy-lab / primitives / governance）

- **执行者**：agent；**依赖**：无；**状态**：observed
- **目的**：核实现有能力、PR 谱系与规范门禁，避免重复建设
- **Agent 必做**：

- 审计三仓库与 PR #23/#24/#28/#29/#30 真实状态；实测本机工具链

- **必须由人完成/提供**：

- 无需操作

- **应交付**：reports/00-preresearch-report.md 审计章节
- **V 证据**：public-source，审计覆盖 PR 谱系与工具链实测；未把历史计划当实现，当前 observed
- **R 遇阻条件**：发现并行会话未提交改动时不处理、不回退，仅记录
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A02 · 电源预算模型（M1 数值基线）

- **执行者**：agent；**依赖**：无；**状态**：observed
- **目的**：计算各模块电流、并发场景、走线宽度与电源门禁
- **Agent 必做**：

- power/power_budget.py：每参数带来源三分法；IPC-2221B 线宽；6 项门禁

- **必须由人完成/提供**：

- 无需操作

- **应交付**：power/budget.json；power/budget.md
- **V 证据**：simulation，6/6 门禁 PASS；常规最坏 1126mA ×1.5 ≤ 3A，当前 observed
- **R 遇阻条件**：数据手册电流未核实的参数标 plan，不得冒充 official
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A03 · 板级接口定义表

- **执行者**：agent；**依赖**：A02；**状态**：observed
- **目的**：9 个连接器 76 引脚的电压/电流/方向/型号定义，作为原理图与机械的共享事实源
- **Agent 必做**：

- interfaces/interfaces.py 单一生成器

- **必须由人完成/提供**：

- 无需操作

- **应交付**：interfaces/interfaces.json；interfaces/interfaces.md
- **V 证据**：simulation，信号名与网表对齐（ERC 交叉检查 0 警告），当前 observed
- **R 遇阻条件**：接口变更必须回写机械参数并重跑装配检查
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A04 · 电子架构 A/B 比较与电源评估

- **执行者**：agent；**依赖**：A03；**状态**：observed
- **目的**：量化比较「Pi+ESP32 协处理器」与「Pi 单主控」，评估 Zero 2 W 内存/音频并发/时延
- **Agent 必做**：

- architecture/architecture.py 加权评分 + Pi 适用性评估

- **必须由人完成/提供**：

- 无需操作

- **应交付**：architecture/architecture.json；architecture/architecture.md
- **V 证据**：simulation，8 准则加权；推荐 A=4.15 vs B=3.43；降级触发条件明确，当前 observed
- **R 遇阻条件**：不预设 ESP32 必须存在——B 案得分输在失效安全，不是成本
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A05 · 架构决策（用户签字）

- **执行者**：human；**依赖**：A04；**状态**：planned
- **目的**：用户确认 V1 采用方案 A 或 B
- **Agent 必做**：

- 提供决策摘要与推荐

- **必须由人完成/提供**：

- 阅读架构比较，回复选择（或提出新约束）

- **应交付**：架构决策记录
- **V 证据**：human-confirmation，用户明确选择；未确认前不进入 PCB 布局，当前 planned
- **R 遇阻条件**：未确认前 A11（EDA 工程）不得开始
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A06 · 初版原理图（网表级）+ ERC-lite

- **执行者**：agent；**依赖**：A03；**状态**：observed
- **目的**：36 器件 49 网络的机器可读完整网表与电气规则检查
- **Agent 必做**：

- eda/netlist.py：单驱动冲突/悬空/电压域/安全默认态/接口对齐

- **必须由人完成/提供**：

- 无需操作

- **应交付**：eda/netlist.json；eda/erc_report.md；eda/environment-status.json
- **V 证据**：simulation，ERC 0 error 0 warning；UART 单驱动；AMP_SD 下拉默认静音，当前 observed
- **R 遇阻条件**：网表不是 EDA 工程——EDA 客户端内工程在 A11 完成
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A07 · 机械参数模型 + 装配验证

- **执行者**：agent；**依赖**：A03；**状态**：observed
- **目的**：PCB 与外壳共享一套参数；真实布尔求交的干涉/净空/公差检查
- **Agent 必做**：

- mech/params.py + build_mech.py（CadQuery）

- **必须由人完成/提供**：

- 无需操作

- **应交付**：mech/mech_params.json；mech/assembly_check.json；mech/outputs/ STEP+STL
- **V 证据**：simulation，20/20 PASS；首轮 4 个 FAIL 已修正并留痕，当前 observed
- **R 遇阻条件**：机械结构未冻结（等试打印公差实测）
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A08 · 视觉两案规格 + 真实渲染

- **执行者**：agent；**依赖**：A07；**状态**：observed
- **目的**：可机器检查的视觉约束 + 参数模型 8 视图渲染 ×2 案
- **Agent 必做**：

- visual/visual_specs.py（12/12 PASS）+ render_blender.py

- **必须由人完成/提供**：

- 盲评打分（V1/V2 匿名）

- **应交付**：visual/visual-specs.json；renders_local/christmas-buddy/*.png
- **V 证据**：simulation，机器检查 12/12；渲染为同一几何源；盲评记录在案，当前 observed
- **R 遇阻条件**：盲评接近时由用户决断或合并优点
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A09 · 数学模型 M1–M5 与 Lean 首批定理

- **执行者**：agent；**依赖**：A02；**状态**：observed
- **目的**：电源/状态机/制造版本的形式化与验证回执
- **Agent 必做**：

- proof/：23 定理；verify_proof.py 公理审计

- **必须由人完成/提供**：

- 无需操作

- **应交付**：proof/src/*.lean；proof/verification.json；proof/README.md；m5_manifest.json
- **V 证据**：simulation，lake build PASS；公理白名单内 0 违规；M5 清单哈希一致，当前 observed
- **R 遇阻条件**：模型证明≠实现正确≠实物验收（三层证据不可互换）
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A10 · 工程任务书生成器 + 工作台集成方案

- **执行者**：agent；**依赖**：A04；**状态**：observed
- **目的**：可调度的结构化任务书（14 任务全要素）与最小工作台集成
- **Agent 必做**：

- scripts/gen_eng_tasks.py + tasks/*.json + 集成方案文档

- **必须由人完成/提供**：

- 无需操作

- **应交付**：tasks/christmas-buddy-v1.tasks.json；tasks/traceability.md；reports/03-workbench-integration.md
- **V 证据**：simulation，需求悬空 0；门禁负责人违规 0；依赖一致，当前 observed
- **R 遇阻条件**：不另起孤立工作台——复用 source-data/workflow.json 与 PR #28 工作台约定
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A11 · EDA 客户端内创建 V1 工程（原理图+DRC）

- **执行者**：agent；**依赖**：A05, A06；**状态**：planned
- **目的**：在嘉立创 EDA 专业版按网表建图，sch_Drc 通过并导出网表比对
- **Agent 必做**：

- CLI/invoke 驱动客户端；必要时手绘辅助

- **必须由人完成/提供**：

- 无需操作

- **应交付**：EDA 工程文件 + 导出网表 + DRC 报告
- **V 证据**：simulation，sch_Drc.check 通过；导出网表与本仓 netlist.json 语义一致，当前 planned
- **R 遇阻条件**：元件 C 编号未核实前不生成制造文件
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A12 · PCB 布局布线 + 3D 联合检查

- **执行者**：agent；**依赖**：A11；**状态**：planned
- **目的**：58×66mm 双面布局，pcb_Drc 通过，STEP 与外壳装配复检
- **Agent 必做**：

- 布线规则按 budget.md 线宽；导出 STEP 进装配检查

- **必须由人完成/提供**：

- 无需操作

- **应交付**：PCB 工程 + DRC/DFM 报告 + PCB STEP
- **V 证据**：simulation，pcb_Drc 0 错误；装配检查含 PCB STEP 后仍 PASS，当前 planned
- **R 遇阻条件**：外形冻结前不下单
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A13 · 外壳细化 + 试打印

- **执行者**：shared；**依赖**：A07；**状态**：planned
- **目的**：螺丝柱/公差/声学细节细化并试打印验证 0.2mm 公差假设
- **Agent 必做**：

- 细化 CAD 与切片；给出打印参数

- **必须由人完成/提供**：

- P1S 打印与试装（或选代打印）

- **应交付**：可打印 STL + 切片 + 试装记录
- **V 证据**：physical-observation，试装间隙与检查模型一致；公差实测回写参数，当前 planned
- **R 遇阻条件**：公差实测前机械结构不冻结
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A14 · 固件：ESP32 HMI + Pi 音频服务

- **执行者**：agent；**依赖**：A11；**状态**：planned
- **目的**：状态机实现与模型适配器测试（合法/非法轨迹 fixtures）
- **Agent 必做**：

- ESP32 灯效/按键/安全路径 + Pi 流式音频管线

- **必须由人完成/提供**：

- 无需操作

- **应交付**：固件源码 + 适配器测试报告
- **V 证据**：simulation，轨迹校验：合法轨迹 TRACE_CONFORMANT、非法轨迹被拒，当前 planned
- **R 遇阻条件**：MAP 未落地前不得声称实现符合模型
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A15 · 制造门禁（人工批准报价）

- **执行者**：human；**依赖**：A12, A13；**状态**：planned
- **目的**：确认 PCB+SMT 报价、数量、风险后放行下单
- **Agent 必做**：

- 整理报价与备选料

- **必须由人完成/提供**：

- 确认付款

- **应交付**：报价确认记录
- **V 证据**：human-confirmation，人明确确认 SKU/数量/运费/风险，当前 planned
- **R 遇阻条件**：无人工确认不产生任何订单
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A16 · 打样与 SMT 下单执行

- **执行者**：vendor；**依赖**：A15；**状态**：planned
- **目的**：嘉立创生产并交付
- **Agent 必做**：

- 生成制造文件包并做哈希绑定

- **必须由人完成/提供**：

- 平台下单、跟踪物流

- **应交付**：制造文件包（哈希绑定）+ 订单回执
- **V 证据**：device-log，Gerber/坐标/BOM 哈希与 m5_manifest 一致，当前 planned
- **R 遇阻条件**：制造文件必须有可追溯哈希
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A17 · 装配与首次通电

- **执行者**：human；**依赖**：A16；**状态**：planned
- **目的**：实物装配、首通电观察
- **Agent 必做**：

- 提供装配指引与检查清单

- **必须由人完成/提供**：

- 焊接/接线/通电（人不被 Agent 代替）

- **应交付**：装配记录 + 首通电记录
- **V 证据**：physical-observation，断电开关/分域保险正常；首通电在受控条件下，当前 planned
- **R 遇阻条件**：首次通电必须人执行
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A18 · 实物测试与验收

- **执行者**：shared；**依赖**：A17；**状态**：planned
- **目的**：电源/音频/时延/安全路径实测对照任务书验收项
- **Agent 必做**：

- 测试脚本与记录表

- **必须由人完成/提供**：

- 按清单实测并确认结果

- **应交付**：实测报告（含不达标项如实记录）
- **V 证据**：physical-measurement，实测峰值≤预算；时延 p50/p95 达标或如实记录，当前 planned
- **R 遇阻条件**：不能用文档完成冒充实测通过
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

### A19 · 教程与工作台归档

- **执行者**：agent；**依赖**：A18；**状态**：planned
- **目的**：零基础可跟做的教程页面与流程样板归档
- **Agent 必做**：

- 项目页/BOM 状态推进/视图重生成

- **必须由人完成/提供**：

- 发布确认

- **应交付**：教程页 + 归档记录
- **V 证据**：simulation，check.py/build.py 通过；双视图无漂移，当前 planned
- **R 遇阻条件**：状态推进需证据支撑
- **深入说明**：[详细教程](/projects/christmas-buddy/01-workflow/)

## 完工报告格式

```text
项目目标 / 当前读者资源：
上游版本与来源（检查日期、实际看到的证据）：
本次已执行动作及输出（Agent 完成 / 人完成 / 供应商完成）：
计划和实测：分别列明，不允许互相替代
阻塞项与实际风险：
需要人做的下一件事：
是否具备付款 / 实物通电 / 公开发布的前提：
```

未经真实观察，不能填写“实测通过”。每次只汇报当前关键关卡，不需把整份原语表重复贴给读者。
