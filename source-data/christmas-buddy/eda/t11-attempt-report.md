# T11 尝试报告：嘉立创 EDA 真实工程建立（Batch 2，时间盒 2026-11-28）

状态：**PARTIAL**（环境与 API 通路全部实测可用；工程对象创建未完成，原因与下一步路径明确）。

## 本轮实测达成

| 项 | 结果 | 证据 |
|---|---|---|
| headless 会话 | ✅ `open --headless true` → alive | session list 记录 |
| `dmt_Project` API 存在性 | ✅ `createProject`（**beta**）等 8+ 方法 | `doc api DMT_Project` |
| createProject 签名 | ✅ `async createProject(projectFriendlyName, projectName, teamUuid, folderUuid, description, collaborationMode=1, fileFormat="eprj3")` | invoke 返回函数源码 |
| 编程建图 API | ✅ `SCH_SourcePrimitiveComponent.add` / `SCH_SourcePrimitiveWire.add` / `SCH_PrimitiveWire.create` | `doc api --search 放置/导线` |
| 真实工程存在性反证 | ✅ **Space Buddy R1 会话有存活本地工程** `~/Documents/LCEDA-Pro/projects/SpaceBuddy-R1/SpaceBuddy-R1.eprj3`（PR #29 会话所有，本会话未触碰） | session list `path` 字段 |

## 未达成与原因

- `createProject({name, dir})` 调用返回 `null`，本地目录未创建。签名要求 **teamUuid/folderUuid**
  （云端团队工作流）：无账号态上下文时无法安全填写。这是**账号/授权依赖**，不是工具能力缺口。
- 由此，原理图绘制（放置元件/连线）、ERC、导出均未执行——没有工程对象就没有可绘制画布。

## 下一步路径（Batch 3，二选一，需用户选择或授权）

1. **云端工程路线**：用户提供 teamUuid（或授权使用其默认团队），createProject → 云端工程 →
   编辑器内绘制与 ERC → 导出工程源文件入库。优点：官方推荐流；缺点：工程主体在云端。
2. **本地 .eprj3 路线**（PR #29 已验证模式）：以 SpaceBuddy-R1/MakerLab-EDA-Check 的本地工程结构为模板
   建立 `~/Documents/LCEDA-Pro/projects/ChristmasBuddy-V1/`，`open --path` 后利用 .eprj3 **磁盘双向同步**
   特性工作，工程目录不入库、只入库导出证据（与本仓 evidence 纪律一致）。

两条路线都保留「C 编号核实后才能放置元件」的门禁（本轮 BOM 全部 CHECK/HOLD，未选型）。

## 证据登记

- 本文件 + `eda/environment-status.json`（CLI/invoke 实测）
- 会话 id：1eb7e16f-7ca8-46f9-9449-1393eead7ddc（已干净关闭）；SpaceBuddy 会话为其他会话资产，未动
