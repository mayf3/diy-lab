# DIY Lab 工作台集成方案（deliverable L，最小 MVP）

原则：**不另起孤立工作台**。复用 diy-lab 现有项目系统（source-data/workflow.json + render_diy_ir 双视图 +
check.py 门禁）、任务系统（tasks-book JSON）与 PR #28 已建的硬件工作台约定；不复制 primitives/governance 仓库。

## 1. Product Engineering 工作流（本项目已按此执行）

```
需求定义(product-spec.json) → 架构设计(architecture/) → 机械 CAD(mech/) → 电子 EDA(eda/)
  → 联合装配验证(build_mech.py 布尔检查) → 视觉审查(visual/ + 渲染 + 盲评)
  → 数学模型(proof/ M1–M5) → Lean 验证(verify_proof.py) → 软件实现(固件，下一阶段)
  → 制造准备(m5_manifest + 报价门禁) → 实物验收(A17/A18 human gate)
```

每阶段落点都是「可检查工件 + 脚本化验收」，由 workflow.json 的 A 任务与 verify 证据类型承载。

## 2. 与现有系统的对接点（已实现）

| 现有系统 | 对接方式 | 状态 |
|---|---|---|
| `source-data/<slug>/workflow.json` + 双视图 | christmas-buddy 完整 DOAVR（19 任务，A01–A10 observed 带证据） | ✅ 本 PR |
| `scripts/check.py` | bom.csv 列/状态枚举、状态一致性、页面规范全部过 | ✅ 本 PR |
| `data/projects.json` | christmas-buddy 条目（planning） | ✅ 本 PR |
| 工程任务书 | `scripts/gen_eng_tasks.py`（通用生成器）→ tasks/*.tasks.json + 追踪矩阵 | ✅ 本 PR |
| 证据管理 | 三分法参数登记 + OBS/EVD 式 evidence_ref + m5_manifest 哈希 | ✅ 本 PR |

## 3. 与 PR #28/#29 硬件工作台的合并计划（不冲突）

PR #28 在 `workbench/`（serve.py:8135、catalog.json）与 `docs/eda/` 建了工作台；PR #29 建 Space Buddy R1 先例。
本 PR 基于 origin/main，**不触碰**这些路径，避免合并冲突。合并顺序建议：

1. 先合 PR #28/#29/#30（工具链文档 + 工作台 + 治理采用记录）。
2. 再合本 PR：`workbench/catalog.json` 增加 christmas-buddy 条目（一行 JSON，合并时由工作台会话或后续小 PR 完成——本 PR 在 `tasks/traceability.md` 留了任务）。
3. catalog 状态字段对齐「工作台六状态」（g_stage/owner/last_completed），Christmas Buddy 的
   A01–A10 对应 G1–G3 附近，映射表写在下一轮。

## 4. 最小 MVP 边界（防止无限扩张）

本轮只新增**三个通用件**：`scripts/gen_eng_tasks.py`（任务书生成器）、
`source-data/<slug>/tasks/product-spec.json` 约定、`m5_manifest.py` 约定（随项目目录走）。
不加数据库、不加服务、不加前端依赖（AGENTS.md 维护最小复杂度）。

未来（有真实需求才做）：任务书 JSON → 站点页面渲染；EDA CLI `--mcp` 接入工作台；
Gerber/BOM 自动报价轮询。这些已登记在任务书之外，不进本轮。
