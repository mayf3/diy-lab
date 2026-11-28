#!/usr/bin/env python3
"""工程任务书生成器（工作台 MVP 能力，deliverable M/L 的核心）。

输入：source-data/<slug>/tasks/product-spec.json（产品需求与验收）
输出：source-data/<slug>/tasks/<slug>-v1.tasks.json + traceability.md

生成规则：
- 按研发阶段模板（需求→架构→EDA→机械→装配→视觉→模型→证明→软件→制造→验收）
  展开，每个任务填齐 8 要素：输入/输出/前置/负责人/依赖/验收/风险/证据。
- 需求追踪矩阵：REQ-* → 任务（机器可查悬空）。
- 门禁任务（gate=true）负责人必须是人（payment/ordering/power-on/red lines）。

用法：python3 scripts/gen_eng_tasks.py christmas-buddy v1
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent

# 阶段模板：id 前缀 → (标题, 负责人, 门禁, 输出物, 证据类型)
STAGES = [
    ("ADT", "仓库与能力审计", "agent", False, "现状审计报告", "REPORT"),
    ("ARC", "电子架构冻结", "human", True, "架构决策记录（用户签字）", "DECISION"),
    ("SCH", "原理图与 EDA 工程", "agent", False, "EDA 工程文件 + 网表导出 + ERC", "EDA_REPORT"),
    ("PCB", "PCB 布局布线与 DRC", "agent", False, "PCB 工程 + DRC/DFM 报告 + STEP", "EDA_REPORT"),
    ("MEC", "机械细化与可打印性", "agent", False, "外壳工程 + 装配检查 + STL/STEP", "CAD_CHECK"),
    ("ASM", "联合装配验证", "agent", False, "PCB×外壳布尔干涉报告", "CAD_CHECK"),
    ("VIS", "视觉渲染与盲评", "shared", False, "8 视图渲染 ×2 案 + 盲评记录", "RENDER+REVIEW"),
    ("MDL", "数学模型与 Lean 证明", "agent", False, "M1–M5 模型 + 验证回执", "LEAN_PROOF"),
    ("FW", "固件（ESP32 + Pi 服务）", "agent", False, "可运行固件 + 模型适配器测试", "TESTED"),
    ("GATE", "制造门禁（人工批准）", "human", True, "报价/数量/风险确认记录", "DECISION"),
    ("FAB", "打样与 SMT 下单执行", "vendor", True, "制造文件包（哈希绑定）+ 订单回执", "RECEIPT"),
    ("BLD", "装配与首次通电", "human", True, "组装记录 + 首通电记录", "OBSERVATION"),
    ("TST", "实物测试与验收", "shared", False, "电源/音频/时延/安全实测报告", "MEASUREMENT"),
    ("DOC", "教程与工作台归档", "agent", False, "项目页 + 视图 + BOM 状态推进", "REPORT"),
]

def load_spec(slug: str) -> dict:
    return json.loads((ROOT / f"source-data/{slug}/tasks/product-spec.json").read_text(encoding="utf-8"))

def build_tasks(slug: str, rev: str) -> list:
    spec = load_spec(slug)
    tasks = []
    prev = None
    for i, (sid, title, owner, gate, output, ev) in enumerate(STAGES):
        tid = f"T-{sid}-1"
        tasks.append({
            "id": tid,
            "title": f"[{sid}] {title}",
            "stage": sid,
            "inputs": [f"source-data/{slug}/tasks/product-spec.json",
                       *([f"前序任务 {prev} 输出"] if prev else ["AGENTS.md / 审计报告"])],
            "outputs": [output],
            "prerequisites": [prev] if prev else [],
            "owner": owner,
            "depends_on": [prev] if prev else [],
            "acceptance": {
                "ADT": "三仓库审计完成，可复用/缺失/修复清单齐备（本轮已交付）",
                "ARC": "用户在架构比较报告上明确选择 A 或 B（本 PR 提供比较与推荐）",
                "SCH": "EDA 客户端工程存在；sch_Drc.check 通过；导出网表与本仓 netlist.json 语义一致",
                "PCB": "pcb_Drc.check 通过；3D STEP 导出并与机械模型联合检查",
                "MEC": "可打印性检查（壁厚/悬撑/公差）通过；试打印切片完成",
                "ASM": "布尔干涉 0 冲突；接插件插拔净空 ≥8mm；USB-C 可达",
                "VIS": "盲评按协议执行且记录在案；优胜方案用户确认",
                "MDL": "verify_proof.py PASS（公理白名单内）；m5_manifest check PASS",
                "FW": "状态机适配器测试（合法/非法轨迹 fixtures）全过；真实设备动作与模型一致",
                "GATE": "用户确认 SKU/数量/运费/风险（付款前人工门禁）",
                "FAB": "嘉立创订单回执 + Gerber/坐标/BOM 哈希与 m5_manifest 绑定一致",
                "BLD": "装配完成记录 + 首次通电观察（人执行，Agent 不得代替）",
                "TST": "电源实测 ≤ 预算；时延 p50/p95 达标或如实记录未达标；安全路径实测",
                "DOC": "check.py/build.py 通过；页面桌面+手机目检记录",
            }[sid],
            "risks": {
                "ADT": "审计遗漏并行会话改动——已核对工作树与 PR 列表",
                "ARC": "架构选择错误导致返工——以降级触发条件约束",
                "SCH": "引脚冲突/封装错误——DRC + 数据手册逐脚核对",
                "PCB": "双面板走线拥挤——外形与接口已按 58×66 预演",
                "MEC": "打印公差超 0.2mm 假设——试打印先行",
                "ASM": "线缆弯曲空间不足——已留 8mm 半径约束",
                "VIS": "盲评两案接近——合并优点再评",
                "MDL": "实现漂移——MAP 未落地前不得声称实现符合模型",
                "FW": "Pi 音频与云链路时延不达标——流式管线为验收项",
                "GATE": "汇率/涨价——下单前重核价格",
                "FAB": "SMT 扩展库料缺货——备选料二选一已在 BOM 登记",
                "BLD": "首次通电异常——断电开关 + 分域 PTC 兜底",
                "TST": "实测不达标——如实记录，不得以文档完成冒充实测通过",
                "DOC": "视图漂移——render_diy_ir.py 自动生成",
            }[sid],
            "evidence": ev,
            "gate": gate,
            "reqs": reqs_for(sid, spec),
        })
        prev = tid
    return tasks

def reqs_for(sid: str, spec: dict) -> list[str]:
    m = {
        "SCH": ["REQ-002", "REQ-005", "REQ-006", "REQ-009", "REQ-011", "REQ-012"],
        "PCB": ["REQ-007", "REQ-012"],
        "MEC": ["REQ-001", "REQ-003", "REQ-004", "REQ-008"],
        "ASM": ["REQ-008", "REQ-010"],
        "VIS": ["REQ-004", "REQ-013"],
        "MDL": ["REQ-005", "REQ-009", "REQ-014"],
        "FW": ["REQ-002", "REQ-005", "REQ-006"],
        "TST": ["REQ-006", "REQ-009", "REQ-010", "REQ-012"],
    }
    return m.get(sid, [])

def main() -> None:
    slug, rev = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "v1")
    spec = load_spec(slug)
    tasks = build_tasks(slug, rev)
    # 追踪矩阵 + 悬空检查
    covered = {}
    for t in tasks:
        for r in t["reqs"]:
            covered.setdefault(r, []).append(t["id"])
    dangling = [r["id"] for r in spec["requirements"] if r["id"] not in covered]
    gate_bad = [t["id"] for t in tasks if t["gate"] and t["owner"] not in ("human", "vendor")]
    deps_ok = all(t["depends_on"][0] == tasks[i - 1]["id"] for i, t in enumerate(tasks) if t["depends_on"])

    book = {
        "schema": "tasks-book/1.0", "product": slug, "rev": rev, "date": date.today().isoformat(),
        "goal": spec["goal"], "non_goals": spec["non_goals"],
        "requirements": spec["requirements"],
        "tasks": tasks,
        "traceability": {r: ts for r, ts in covered.items()},
        "checks": {"dangling_reqs": dangling, "gate_owner_violations": gate_bad, "deps_linear_ok": deps_ok},
    }
    out_dir = ROOT / f"source-data/{slug}/tasks"
    (out_dir / f"{slug}-{rev}.tasks.json").write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [f"# {spec['title']} · {rev} 工程任务书（生成于 {date.today().isoformat()}）", "",
          f"目标：{spec['goal']}", "",
          "## 非目标", ""] + [f"- {n}" for n in spec["non_goals"]] + ["", "## 任务列表", ""]
    for t in tasks:
        gate = " **【门禁·须人批准】**" if t["gate"] else ""
        md += [f"### {t['id']} {t['title']}{gate}", "",
               f"- 负责人：{t['owner']}｜依赖：{'、'.join(t['depends_on']) or '—'}｜覆盖需求：{'、'.join(t['reqs']) or '—'}",
               f"- 输入：{'；'.join(t['inputs'])}",
               f"- 输出：{t['outputs'][0]}",
               f"- 验收：{t['acceptance']}",
               f"- 风险：{t['risks']}",
               f"- 证据类型：{t['evidence']}", ""]
    md += ["## 需求追踪矩阵", "", "| 需求 | 任务 |", "|---|---|"]
    for r in spec["requirements"]:
        md.append(f"| {r['id']} | {'、'.join(covered.get(r['id'], ['⚠ 未覆盖']))} |")
    md += ["", "## 机器检查", "",
           f"- 需求悬空：{dangling or '无'}",
           f"- 门禁负责人违规：{gate_bad or '无'}",
           f"- 依赖线性一致：{deps_ok}", ""]
    (out_dir / "traceability.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ok = not dangling and not gate_bad and deps_ok
    print(f"tasks book: {len(tasks)} tasks, dangling={dangling or 0}, gate_violations={gate_bad or 0}, deps_ok={deps_ok}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
