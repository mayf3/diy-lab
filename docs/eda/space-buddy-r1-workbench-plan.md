# Space Buddy Deck R1 × 工作台升级：审计、差距与实施计划

**日期：2026-11-27 · 审计人：本地 Agent（ZCode 会话）· 状态：计划已批准执行（发起人 2026-11-27 指示）**

## 一、审计结果（全部为本机实测与精确 commit，非记忆）

### 1. 三个仓库与工作树

| 仓库/工作树 | 精确状态 |
| --- | --- |
| `mayf3/diy-lab`（GitHub） | main + 两个 OPEN PR：#27（记录器采购执行轮，`feat/recorder-v1-buildkit`@63e977f）、#28（本工作树，`codex/eda-pcba-setup-20261126`@6d12b72→d551ac2） |
| 本地主工作树 `DIY/diy-lab` | 分支 `feat/recorder-v1-buildkit`@63e977f（已推送），无未提交变更 |
| 本地工作树 `DIY/diy-lab-pcba` | 分支 `codex/eda-pcba-setup-20261126`，干净，领先 origin/main 5 个提交，CI validate PASS |
| `mayf3/primitives` | 本地克隆 `DIY/primitives`，采用基线 commit **`67212e487e7e0c5040ba866b51a9de99bf6a0ecb`**（2026-11-27 08:06 +08:00；含当日更新的 MODEL_CENTERED_DEVELOPMENT v0.1.0） |
| `mayf3/agent-development-governance` | 本地克隆 `DIY/agent-development-governance`，采用基线 commit **`403cba321dd309410043f42a35807533e3660387`**（VERSION 2.0.0-rc.5；SPEC_GOVERNANCE_V1.0.0，ENFORCEMENT=manual_semantic_policy_plus_deterministic_integrity） |
| 注意 | governance 的 .agents/README 自身钉住 primitives `c7161dc`（更早）；本项目按发起人指示采用 primitives 最新 main `67212e4`，两者的差异（MODEL_CENTERED_DEVELOPMENT v0.1.0 为当日新增）已评估为适用 |

### 2. 嘉立创 EDA 实况（2026-11-27 上午实测）

- doctor：connected=true、bridgeVersion=4.1.105.0339a6cd、versionMatch=true
- 当前两个主进程：owner 33464（11-26 19:40 启动，已激活编辑器）+ 60353（11-27 08:06，ChatGPT Codex 拉起的 MCP 实例，已清理）
- 已核实的 API：doc api（SYS_Environment/SYS_FileSystem/DMT_Project/DMT_Board/DMT_EditorControl/SCH_Document/PCB_Document/SCH_PrimitiveText/PCB_PrimitiveString/lib_Device 全套签名）；`lib_Device.search` 可用但**扩展件库搜索在客户端重启后短暂返回空**（云同步恢复即正常）
- 审计工程：`MakerLab-EDA-Check-20261126`（eprj3，仅工具链验证用，禁止进入制造包）

### 3. 硬件工作台实况

- 8135 服务在线（LaunchAgent `com.mayf3.hardware-workbench`），`/api/status` 实测：**ready=true**，bridge=connected，activation=**verified**（2026-11-26 验收），editor_round_trip=**passed**（evidence_at 2026-11-26T14:08+08:00）
- 21/21 后端测试通过；8123 教程站 200 不受影响

### 4. Button Deck 现状（R1 方向已由发起人确认）

- R1 = 原生 USB HID 键盘（F13–F16），真键盘模式，不依赖常驻 bridge；UART 口保留烧录维护
- 已有：R1 修订文档、HID 固件草稿（未编译）、概念效果图（**1×4 布局、旧配色——待按 Space Buddy R1 规格修订**）
- 官方核实：J1/J3 各 22 针、GPIO4–7=J1.4–7、GND=J1.22+J3.1/21/22、OTG 单口供电为官方推荐
- 元件候选（EDA 库内 C 号）：Omron B3F-4055（C9900023790）、无声贴片 6×6×5（C9900014294）、11P 排母（C9900027094）；**1×22P 单件库内未见 → 每侧 2×11P 拼接**
- 库搜索在客户端重启后曾返回空（云同步恢复即正常）；立创现价/库存受搜索配额限制未逐项核实

## 二、差距分析（对照目标架构）

| 目标 | 现状 | 差距 | 归属 |
| --- | --- | --- | --- |
| A. DIY Lab = 唯一项目入口（产品→版本→阶段→产物→验收） | 工作台已有项目/文档/备注/状态 | 产品条目仍是旧名“四键 Button Deck”+ 旧 USB-UART 路线；缺 G0–G8 门禁、缺“当前 Agent/最近完成/是否需用户决策”字段 | **PR-A** |
| B. 制造能力层（EDA/PCBA/BOM/CPL/STEP/3D 打印/报价） | EDA CLI 已可用；工作台不重复实现 EDA ✓ | 制造状态模型（Designed→…→Accepted）未定义；嘉立创 3D 打印/报价入口未接 | PR-A（模型）+ PR-B（产物） |
| C. 治理/数学建模采用 | diy-lab 无 `docs/governance/development-method-adoption.md` | 建立采用记录（精确上游 commit）；Space Buddy M1–M4 模型未建立 | **PR-C** + PR-B |
| Space Buddy Deck R1 视觉与产品定义 | 概念图为 1×4 旧配色 | 2×2 布局、奶油白主体、薰衣草紫底座、四色键帽（珊瑚橙/星空蓝/薄荷绿/暖黄）、太空图案（火箭/星球/星星/月亮）、宇航员头像、舷窗装饰——全部待按规格修订 | **PR-B** |
| 新旧 USB 合同不一致 | interface-contract.md 仍为 UART 为主，R1 修订文档并行存在 | 统一口径：产品路线=HID（R1），UART 合同降级为烧录/维护附录 | **PR-A** |
| G0–G8 门禁 | 未定义 | 建立门禁定义与工作台阶段映射 | **PR-A**（定义+映射），PR-B/C 按门禁执行 |

## 三、实施计划（三个独立 PR）

### PR-A：工作台与制造能力整合（本分支 `codex/eda-pcba-setup-20261126`，即 #28 的延续）

1. `source-data/productization/projects.json`：agent-button-deck → **Space Buddy Deck R1**（名称、路线=HID 载板、阶段=G0 视觉冻结、开放项=四键用途/手感/DevKitC SKU/OTG 口实物/F13-F16 绑定清单）。
2. `workbench/catalog.json`：button-deck 的 tagline/stages/artifacts 按 Space Buddy R1 + G0–G8 更新；documents allowlist 增加 R1 修订文档、HID 固件草稿、概念效果图。
3. `interface-contract.md` 顶部加 R1 路线声明（HID 为产品路线；UART 章节降级为烧录/维护附录，保留历史证据价值）。
4. `build_data.py` 生成数据同步；`workbench/README.md` 导航合同补充。
5. 验收：21 项测试全绿 + build_data 生成一致 + serve --check + scripts/check.py。

### PR-B：Space Buddy Deck R1 设计与产品工程（新分支 `feat/space-buddy-r1`，基于 PR-A）

1. `pcba-v1/space-buddy-r1-spec.md`：视觉规格冻结文本（2×2、四色键帽、太空图案、宇航员头像、舷窗、薰衣草紫底座、双 USB 口后置、底部螺丝+脚垫）。
2. M1 电气连接模型 / M2 机械结构模型 / M3 制造状态模型（Designed→Accepted 七态进入条件与证据）/ M4 视觉设计模型——先文档化；Lean 仅在电气连接模型的稳定子集评估（不为本而扩大范围）。
3. 概念效果图修订为 2×2 Space Buddy 版（视觉基准），保持“概念/尺寸未冻结”标注。
4. G0 门禁验收：发起人确认视觉冻结 → 进入 G1（真实硬件型号与机械尺寸确认）。

### PR-C：研发治理与模型/证明采用（新分支 `feat/governance-adoption`，基于 PR-A）

1. `docs/governance/development-method-adoption.md`：primitives@`67212e4`、governance@`403cba3`（VERSION 2.0.0-rc.5）的采用记录；适用范围（关键状态/权限/持久化/接口/制造约束）；版本更新与重新验收方式（上游变更→consumer-local impact assessment→按 PR 重新绑定）。
2. 不复制上游仓库；Space Buddy M1–M3 建模引用 primitives 方法规范与固定 commit。
3. AGENTS.md 增补一段治理入口（或以链接方式指向 adoption 文档）。

## 四、G0–G8 门禁定义（Space Buddy Deck R1）

| 门禁 | 内容 | 进入条件 | 产物/证据 | 负责人 |
| --- | --- | --- | --- | --- |
| G0 视觉与产品定义冻结 | 视觉规格+产品需求冻结 | 概念效果图发起人确认 | 规格文档+确认记录 | Agent 出稿，发起人确认 |
| G1 真实硬件型号与机械尺寸确认 | DevKitC SKU、开关/排母实物、尺寸 | 元件到货或官方尺寸图 | 核对记录+照片 | 发起人下单，Agent 核对 |
| G2 CAD 外壳与内部结构设计 | 参数化外壳/载板布局 | G1 冻结 | STL/3MF+切片 | Agent |
| G3 CAD 视觉与机械验证 | 渲染对照+干涉检查 | G2 | 验证记录 | Agent+发起人评审 |
| G4 原理图及 PCB 设计 | 原理图/PCB/网络核对 | G1 | 原生工程+检查结果 | Agent |
| G5 PCB 与外壳联合验证 | 板壳配合 | G2+G4 | 联合渲染/试装小样 | Agent |
| G6 制造资料与工厂能力确认 | Gerber/BOM/CPL/STEP+代焊范围 | G5 | 制造包+工厂确认 | Agent |
| G7 人工批准报价与打样 | 发起人批准并付款 | G6 | 订单记录 | **发起人** |
| G8 实物组装与功能验收 | 四键 10 次/键、USB 重插、装壳操作 | G7+到货 | 实测记录 | 发起人+Agent 协作 |

## 五、优先级与边界

- 优先级：**产品（Space Buddy R1 做出来）> 工作台如实呈现 > 治理文档**。
- 不做：不为治理而重构工作台全部代码；不给普通文案改动写 Lean；不复制上游仓库；不在未获授权时下单/付款/烧录。
- 本轮已执行：PR-A 第 1–3 项（见提交）；PR-B/PR-C 依次推进。
