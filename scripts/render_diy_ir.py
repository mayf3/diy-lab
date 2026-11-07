#!/usr/bin/env python3
"""Validate and render one source of DIY facts into human and Agent reading views.

DOAVR v0.1 is an experimental lightweight contract, not a manufacturing standard.
Run: python3 scripts/render_diy_ir.py [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "source-data"
ACTORS = {"agent", "human", "shared", "vendor"}
EVIDENCE = {"public-source", "simulation", "human-confirmation", "human-approval",
            "physical-measurement", "physical-observation", "device-log"}
OUTCOMES = {"planned", "observed", "failed", "blocked"}

def validate(data: dict, path: Path) -> list[str]:
    issues: list[str] = []
    def bad(msg: str) -> None:
        issues.append(f"{path.relative_to(ROOT)}: {msg}")

    if data.get("schema_version") != "0.1":
        bad("schema_version must equal 0.1")
    slug = data.get("project", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        bad("project slug must be lowercase-hyphen-safe")
    if slug != path.parent.name:
        bad("project slug must equal parent directory")
    goal = data.get("direction", {})
    if not goal.get("goal") or not goal.get("done_when") or not goal.get("audience"):
        bad("direction requires goal, done_when, audience")
    if not data.get("resource_routes"):
        bad("resource_routes cannot be empty; public guide must not assume equipment")
    for route in data.get("resource_routes", []):
        if len(route.get("options", [])) < 2 or not route.get("policy"):
            bad("each route needs at least two options and a policy")
    tasks = data.get("tasks", [])
    if not tasks:
        bad("tasks cannot be empty")
    ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"A\d{2,3}", str(i)) for i in ids):
        bad("task ids must be unique, e.g. A01")
    seen: set[str] = set()
    for task in tasks:
        tid = task.get("id", "?")
        if task.get("actor") not in ACTORS:
            bad(f"{tid} invalid actor")
        if not task.get("human_summary"):
            bad(f"{tid} missing concise human_summary for novice view")
        if not all(task.get(k) for k in ("title", "goal", "outputs", "block", "deep")):
            bad(f"{tid} missing title, goal, outputs, blocked strategy or deep link")
        if not isinstance(task.get("agent", []), list) or not isinstance(task.get("human", []), list):
            bad(f"{tid} agent/human instructions must be arrays")
        if task.get("actor") in {"agent", "shared"} and not task.get("agent"):
            bad(f"{tid} must have concrete Agent tasks")
        if task.get("actor") in {"human", "shared"} and not task.get("human"):
            bad(f"{tid} must state human's actual responsibility")
        if task.get("actor") == "agent" and task.get("verify", {}).get("type") in {"physical-observation","physical-measurement", "device-log", "human-approval"}:
            bad(f"{tid} pure Agent step cannot certify physical observation/approval")
        if task.get("verify", {}).get("type") not in EVIDENCE or not task.get("verify", {}).get("criteria"):
            bad(f"{tid} invalid verification criteria/type")
        if task.get("verify", {}).get("status") not in OUTCOMES:
            bad(f"{tid} verification must include planned/observed/failed/blocked status")
        if task.get("verify", {}).get("status") == "observed":
            if not task["verify"].get("evidence_ref") or not task["verify"].get("observed_on"):
                bad(f"{tid} observed verification needs evidence_ref and observed_on; plans are not evidence")
        for dep in task.get("requires", []):
            if dep not in seen:
                bad(f"{tid} dependencies must reference earlier existing tasks: {dep}")
        if not task.get("deep", "").startswith("/projects/" + slug + "/"):
            bad(f"{tid} deep link must target this project")
        seen.add(tid)
    for ref in data.get("references", []):
        if not ref.get("url", "").startswith("https://"):
            bad("all external reference links need https")
    return issues

def bullet(items: list[str], empty: str = "本关不要求你操作。") -> str:
    if not items:
        return empty + "\n"
    return "".join(f"- {item}\n" for item in items)

def route_table(data: dict) -> str:
    lines = ["| 先看条件 | 你可以选什么 | AI 应如何分流 |",
             "| --- | --- | --- |"]
    for route in data.get("resource_routes", []):
        lines.append(f"| {route['question']} | {' / '.join(route['options'])} | {route['policy']} |")
    return "\n".join(lines) + "\n"

def md_human(data: dict) -> str:
    name = data["project"]
    result = [
      f"# {data.get('display_name', name)}｜新手制作路线（人类版）", "",
      "> **自动生成·工作流仍是计划，不是实物测试报告。** 本页由 source-data/" + name + "/workflow.json 生成；不能把 AI 看过网页、切片预览或用户勾选说成已经制作成功。", "",
      "你不需要自己翻 GitHub README、核对原理图或判断屏幕排线。**把具体调查交给有文件和网络访问权限的 Agent**；你只做目标选择、必要的实物操作、付款和实机验收。如果没有 Agent，仍可以点击每一关的详细教程按传统方式进行。", "",
      f"**目标**：{data['direction']['goal']}。",
      f"**完成标准**：{data['direction']['done_when']}。", "",
      "## 先选择你自己的资源条件", "",
      route_table(data),
      "详细说明：[如何让 Agent 帮你做](/guide/agent-first/) · [DIY 原语方法](/guide/diy-primitives/) · [Agent 执行版](/projects/" + name + "/agent-track/)。", "",
      "## 一句话委托 Agent", "",
      "> 项目执行规范：https://mayf3.github.io/diy-lab/projects/" + name + "/agent-track/ 。请先阅读此规范与公开上游工程。不要让我替你核查 GitHub、PCB、BOM 或下载文件；你负责调查、判断证据等级、按我的设备条件制定制作/代打印路径并给出精确 SKU 与报价。不能访问的资料请只向我索取具体文件。未经我批准，不付款、不写设备固件、不进行有风险的实物操作。每一步只告诉我你做了什么、我还要动手做什么、怎么看结果及出错后怎么办。", "",
      "## 按顺序制作（12 关）", ""
    ]
    for i,t in enumerate(data["tasks"], 1):
        result += [
          f"### 第 {i} 关｜{t['title']}", "",
          f"**这一关要拿到：** {t['goal']}。", "",
          "**交给 Agent 完成**：", "", t["human_summary"], "",
          "**你亲自做**：", "", bullet(t["human"]), "",
          f"**完成时应该有：** {'、'.join(t['outputs'])}。", "",
          f"**怎样判断：** {t['verify']['criteria']}。**当前证据状态：{t['verify']['status']}**（未运行不能算通过）。", "",
          f"**卡住或失败：** {t['block']}", "",
          f"[展开这关的图文细节]({t['deep']})", ""
        ]
    result += [
        "## 最后一步：只记录真实发生过的事", "",
        "如果尚未购买、尚未打印、没有实测日志，就如实标记“未做/待验证”。不把 Agent 的资料检索报告、几何模拟或进度勾选冒充物理验收。",
        "公开视频与照片时，检查版权、订单地址、设备标识及个人信息；外部工程只链接上游，不擅自转载。", ""
    ]
    return "\n".join(result).replace("\n\n\n", "\n\n")

def md_agent(data: dict) -> str:
    name = data["project"]
    lines = [
      f"# {data.get('display_name', name)}｜Agent 执行规范（机器工作流视图）", "",
      "> **自动生成·规范草案，未代表真实执行。** 唯一规范源：source-data/" + name + "/workflow.json。源资料需在执行当天重新检索；不要将下列 planned 标记为 verified。", "",
      f"**D（目标）**：{data['direction']['goal']}。", "",
      f"**受众约束**：{data['direction']['audience']}。", "",
      "**禁止误解为目标**：", "", bullet(data["direction"].get("non_goals", [])), "",
      "## 启动协议", "",
      "1. 读取当前用户的设备/预算/技能约束；**只问缺少且会改变实际方案的信息**。不要假设用户有 P1S 或 Mac。",
      "2. 自行获取官方 GitHub、工程文件、BOM 和 Release；对上游每一个关键型号/版本记录来源、时间、可验证范围。",
      "3. 可用工具能读到的页面、CAD、PCB、规格和报价，**自己调用工具检查**，不要把“去看源码”转交给用户。工具受限时请求最低限度文件，不编造已检查。",
      "4. 报告每一关的状态：planned / observed / failed / blocked，输出证据位置、影响以及下一步。**模拟 ≠ 实物、读取 ≠ 验收、建议 ≠ 批准付款。**",
      "5. 对付款、不可逆烧录、焊接、儿童使用、安全相关动作，要求真实用户决定或现场证据；不绕过安全检查。", "",
      "## O（资源选择和替代路线）", "", route_table(data),
      "## 官方上游参考（执行时复核）", ""
    ]
    for ref in data.get("references", []):
        lines.append(f"- {ref['role']}：[来源]({ref['url']})")
    lines += ["", "## A/V/R（动作、证据、依赖与阻断）", ""]
    for task in data["tasks"]:
        lines += [
          f"### {task['id']} · {task['title']}", "",
          f"- **执行者**：{task['actor']}；**依赖**：{', '.join(task['requires']) or '无'}；**状态**：{task['status']}",
          f"- **目的**：{task['goal']}",
          "- **Agent 必做**：", "", bullet(task["agent"]), "",
          "- **必须由人完成/提供**：", "", bullet(task["human"]), "",
          "- **应交付**：" + "；".join(task["outputs"]),
          f"- **V 证据**：{task['verify']['type']}，{task['verify']['criteria']}，当前 {task['verify']['status']}",
          f"- **R 遇阻条件**：{task['block']}",
          f"- **深入说明**：[详细教程]({task['deep']})", ""
        ]
    lines += [
      "## 完工报告格式", "",
      "```text",
      "项目目标 / 当前读者资源：",
      "上游版本与来源（检查日期、实际看到的证据）：",
      "本次已执行动作及输出（Agent 完成 / 人完成 / 供应商完成）：",
      "计划和实测：分别列明，不允许互相替代",
      "阻塞项与实际风险：",
      "需要人做的下一件事：",
      "是否具备付款 / 实物通电 / 公开发布的前提：",
      "```", "",
      "未经真实观察，不能填写“实测通过”。每次只汇报当前关键关卡，不需把整份原语表重复贴给读者。", ""
    ]
    return "\n".join(lines).replace("\n\n\n", "\n\n")

def run(check: bool = False) -> int:
    problems: list[str] = []
    count = 0
    for path in sorted(WORKFLOWS.glob("*/workflow.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            problems.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
            continue
        problems.extend(validate(data, path))
        if problems:
            continue
        name = data["project"]
        outputs = {
            ROOT / "content" / "projects" / name / "human-track.md": md_human(data),
            ROOT / "content" / "projects" / name / "agent-track.md": md_agent(data)
        }
        for dest, text in outputs.items():
            if check:
                if not dest.exists() or dest.read_text(encoding="utf-8") != text:
                    problems.append(f"{dest.relative_to(ROOT)}: generated view is stale; run python3 scripts/render_diy_ir.py")
            else:
                dest.write_text(text, encoding="utf-8")
        count += 1
    if problems:
        print("DIY IR validation failed:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"DIY IR: {count} project(s) {'consistent' if check else 'rendered'}; two views per project.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify generated human/agent views are current")
    args = parser.parse_args()
    sys.exit(run(check=args.check))
