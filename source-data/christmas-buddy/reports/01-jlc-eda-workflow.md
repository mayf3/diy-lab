# 嘉立创 EDA 工作流研究报告（deliverable B）

查看日期：2026-11-28。所有结论区分「官方文档核实」「本机实测」「待验证」。

## 1. 工具形态与能力（官方文档核实）

**嘉立创EDA专业版**（prodocs.lceda.cn）：

- **官方 CLI 内置于客户端**（V4.1.60+）：`open`（返回会话 id，支持 `--headless true` 无界面模式）、
  `invoke`（在会话中执行 JS，`--fn/--args/--timeout`）、`doctor`、`session list/close/abort`、
  `doc api/external/format`（渐进式 API 查询 + `--search`）、`--mcp stdio|http`（官方 MCP 服务器模式）。
- **扩展 API 命名空间**：SYS_\*（系统）、DMT_\*（文档树/工程）、SCH_\*（原理图）、PCB_\*（PCB/DRC/DFM/自动布线）、
  PNL_\*（拼板）、LIB_\*（综合库：器件/符号/封装/3D/仿真模型）。
- **设计验证 API**：`sch_Drc.check` / `pcb_Drc.check`（含原理图-PCB 网表比对）；
  **制造输出 API**：`sch_ManufactureData.getNetlistFile/getBomFile/getPngFile`、
  `pcb_ManufactureData.get3DFile()`（STEP）+ Gerber / 坐标文件 / IPC-2581 / ODB++ / PDF。
- **官方扩展 SDK**：github.com/easyeda/easyeda-api-sdk（Apache-2.0，TypeScript，构建为 .eext；
  2026-11-17 有推送，活跃）。
- **元件数据 API（easyeda2kicad 所用端点，非官方保证）**：
  `easyeda.com/api/products/{lcsc_id}/components`（符号/封装）、`modules.easyeda.com/3dmodel/{uuid}`（OBJ/STEP）、
  JLCPCB SMT 元件匿名搜索 API。工具自声明不保证转换正确性——只作选型辅助，不替代人工核对。

## 2. 本机实测（2026-11-28，Christmas Buddy 分支独立复核）

| 检查 | 结果 |
|---|---|
| CLI `--help` | ✅ JLCEDA Pro 4.1.105.0339a6cd，全部子命令在列 |
| `doctor` | ✅ 端点 JLCEDAPro5647a773 响应 |
| `doc api --search 放置/导线` | ✅ 命中 `SCH_SourcePrimitiveComponent.add`、`SCH_SourcePrimitiveWire.add` 等编程建图 API |
| `open --headless true` | ✅ 会话 alive（headless=true） |
| `invoke --code "return 1+1"` | ✅ 返回 2；`Object.keys(eda)` 暴露 dmt_Project/dmt_Schematic/lib_Device/pcb_Drc/pcb_Dfm/pcb_ManufactureData 等全命名空间 |
| `session close` | ✅ 干净退出 |

证据登记：`source-data/christmas-buddy/eda/environment-status.json`。
更早的独立复核（安装+激活+编辑器往返）见 PR #28 分支 `docs/eda/environment-status.json`（2026-11-26）。

## 3. 可自动化的工作流（推荐流水线）

```
netlist.json（本仓单一事实源）
  → invoke: LIB_Device 按 C 编号取符号/封装 → SCH_SourcePrimitiveComponent.add 放置
  → SCH_SourcePrimitiveWire.add 连线 → sch_Drc.check
  → sch_ManufactureData.getNetlistFile 导出网表 ↔ 本仓 netlist.json 语义比对（自写 checker）
  → PCB 布局（人工+API 辅助）→ pcb_Drc.check → pcb_ManufactureData 导出 Gerber/坐标/BOM/STEP
  → Gerber/坐标/BOM 哈希写入 m5_manifest.json（OB-1 义务闭合）
```

- 版本管理：`.eprj3` 目录工程与编辑器双向同步（磁盘编辑自动重载），可入 Git；
  设计工件哈希由 `m5_manifest.py` 绑定。
- UI 自动点击：**明确不采用**（任务书红线）；一切验证走 API/文件格式比对。

## 4. 已知边界与风险

1. 官方 CLI 文档仅给 Windows 路径示例——macOS 可用性靠本机实测支撑（已过，但客户端升级后需复测）。
2. `editor_round_trip passed` ≠ 电路正确 ≠ 可制造（governance 门禁原话）。
3. 元件 C 编号与现价：本轮网络受限未逐项核实，BOM 全部标 CHECK/HOLD——下单轮必须逐项核对
   （含基本库/扩展库属性、封装库存、钢网要求）。
4. `pcb_Drc.check` 是设计规则检查；嘉立创下单系统的 DFM 审核是另一道（下单时发生），二者不可互替。

## 5. 与其他工具的关系

- KiCad/easyeda2kicad 路线可用但非必须：既然官方 CLI+扩展 API 本机可用，直接走嘉立创原生路线，
  避免「KiCad 设计 → 导入转换 → 再核对」的额外损耗。
- `--mcp stdio` 模式为未来把 EDA 接入 Agent 工作台提供了官方通道（PR #28 工作台可评估接入）。
