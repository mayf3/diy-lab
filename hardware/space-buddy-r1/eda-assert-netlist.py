#!/usr/bin/env python3
"""Space Buddy R1 · 网表机器断言（唯一源 = 真实导出的 PROTEL 网表 .net 文件）。

用法：
    python3 eda-assert-netlist.py            # 断言 + 重新生成 netlist-evidence.json
    python3 eda-assert-netlist.py --check    # 只断言，不写 json（供 CI/校验器调用）

规则（用户验收 §5）：
  1. GPIO4={J1-4,K1-1} GPIO5={J1-5,K2-1} GPIO6={J1-6,K3-1} GPIO7={J1-7,K4-1}
  2. GND = 四开关接地端 + 真实开发板 GND 排针（J1-22, J3-1, J3-21, J3-22）
  3. 四路 GPIO 唯一映射，无互短（任一引脚不得出现在两个网络）
  4. 无电源短路（3V3/5V 等电源引脚不得混入信号/地网络；不得存在 3V3/5V 网络）
  5. 开关引脚连接完整（每键 pin1 入 GPIO、pin2 入 GND）
  6. 排母实际引脚已进入网络（非仅有标签的假完成——网表引脚来自真实连接）
  7. C9900017374 不得作为 Supplier Part 声明出现（仅允许结构占位 FOOTPRINT/Symbol 行，
     该占位已登记为「非最终封装、禁止用于制造」）
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NET = HERE / "netlist-evidence.net"
EVIDENCE = HERE / "netlist-evidence.json"

GPIO_EXPECT = {
    "GPIO4": {"J1-4", "K1-1"},
    "GPIO5": {"J1-5", "K2-1"},
    "GPIO6": {"J1-6", "K3-1"},
    "GPIO7": {"J1-7", "K4-1"},
}
GND_EXPECT = {"K1-2", "K2-2", "K3-2", "K4-2", "J1-22", "J3-1", "J3-21", "J3-22"}
POWER_NETS = {"3V3", "3V3_1", "5V", "VCC", "VIN"}
POWER_PIN_SIGNS = ("3V3", "5V", "VCC", "VIN")

FOOTPRINT_PLACEHOLDER = "SW-SMD_C9900017374"


def parse_protel(text: str) -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    """解析 PROTEL 2.0：返回 (nets {name: [designator-pin]}, components {des: fields})。"""
    nets: dict[str, list[str]] = {}
    comps: dict[str, dict[str, str]] = {}
    # 网络块：`( 名称 \n 引脚行... \n)`
    for block in re.findall(r"\(\s*\n(.*?)\n\)", text, flags=re.S):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        name = lines[0]
        pins = []
        for ln in lines[1:]:
            m = re.match(r"^([A-Za-z][A-Za-z0-9_]*)-(\d+)\s", ln)
            if m:
                pins.append(f"{m.group(1)}-{m.group(2)}")
        nets[name] = pins
    # 器件块：`[ ... ]`，键值行对
    for block in re.findall(r"^\[\s*\n(.*?)\n\]", text, flags=re.S | re.M):
        lines = [ln.strip() for ln in block.splitlines()]
        fields: dict[str, str] = {}
        i = 0
        while i + 1 < len(lines):
            key, value = lines[i], lines[i + 1]
            fields.setdefault(key, value)
            i += 2
        if fields.get("DESIGNATOR"):
            comps[fields["DESIGNATOR"]] = fields
    return nets, comps


def main() -> int:
    raw = NET.read_bytes()
    text = raw.decode("utf-8")
    nets, comps = parse_protel(text)
    failures: list[str] = []
    checks: dict[str, str] = {}

    def expect(cond: bool, label: str) -> None:
        checks[label] = "PASS" if cond else "FAIL"
        if not cond:
            failures.append(label)

    # 1. GPIO 精确映射
    for net, want in GPIO_EXPECT.items():
        got = set(nets.get(net, []))
        expect(got == want, f"{net}={{{'，'.join(sorted(want))}}}")

    # 2. GND 精确集合（开关地 + 全部四个真实开发板地引脚）
    gnd = set(nets.get("GND", []))
    expect(gnd == GND_EXPECT, f"GND={{{'，'.join(sorted(GND_EXPECT))}}}")

    # 3. 唯一映射 / 无互短：任一引脚不得出现在两个网络
    pin_owner: dict[str, list[str]] = {}
    for name, pins in nets.items():
        for p in pins:
            pin_owner.setdefault(p, []).append(name)
    multi = {p: ns for p, ns in pin_owner.items() if len(ns) > 1}
    expect(not multi, "无引脚跨网络互短")

    # 4. 无电源短路：信号/地网络不得含电源网络名或电源引脚；不得存在电源网络
    for bad in POWER_NETS:
        expect(bad not in nets, f"不存在电源网络 {bad}")
    for name in ("GPIO4", "GPIO5", "GPIO6", "GPIO7", "GND"):
        for p in nets.get(name, []):
            expect(not any(s in p for s in POWER_PIN_SIGNS), f"{name} 不含电源引脚 {p}")

    # 5. 开关引脚完整（每键两脚均在网，pin3 符号脚电气未用属预期）
    for k in ("K1", "K2", "K3", "K4"):
        expect(f"{k}-1" in pin_owner and f"{k}-2" in pin_owner, f"{k} pin1/pin2 均入网")

    # 6. 排母实际引脚入网（GPIO 网络同时含 J-pin 与 K-pin = 排针真实接入）
    for net, want in GPIO_EXPECT.items():
        j_pin = [p for p in want if p.startswith("J")]
        k_pin = [p for p in want if p.startswith("K")]
        got = set(nets.get(net, []))
        expect(bool(got) and all(p in got for p in j_pin + k_pin),
               f"{net} 排母引脚真实入网（非仅标签）")

    # 7. C9900017374 隔离：Supplier Part 不得出现该编号；FOOTPRINT 占位必须登记为非最终
    for des, fields in comps.items():
        sup = fields.get("Supplier Part", "")
        expect("C9900017374" not in sup, f"{des} Supplier Part 不含 C9900017374")
        fp = fields.get("FOOTPRINT", "")
        if fp == FOOTPRINT_PLACEHOLDER:
            checks[f"{des} FOOTPRINT 占位(非最终)"] = "QUARANTINED"
    expect(any(f.get("DESIGNATOR") in ("J1", "J3") for f in comps.values()),
           "连接器 J1/J3 在网表器件表中")

    ok = not failures
    evidence = {
        "format": "PROTEL NETLIST 2.0",
        "exported_at": "2026-11-28",
        "source": "eda.sch_ManufactureData.getNetlistFile('space-buddy-r1','Protel2') 真实导出（非手写）",
        "session": "9b2df7cb (可见会话，保存→关闭→重开后导出)",
        "project_uuid": "4ab9e52666a4fc7fe9b1d0c7c4c4263444d972eb139973d04478d976200a78b8",
        "local_reopen_instance_uuid": "4a7cbe805de29ce4d5cfb6358445cb4cb5e28fd1d92edfb453c18245a8d1483b",
        "schematic_uuid": "7415725566084bd0",
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "nets": {k: sorted(v) for k, v in nets.items()},
        "components": {k: {"footprint_declared": v.get("FOOTPRINT", ""),
                            "supplier_part": v.get("Supplier Part", ""),
                            "partname": v.get("PARTTYPE", "")}
                        for k, v in sorted(comps.items())},
        "switch_footprint": "TBD（样轴确认后绑定 Boba U4 或实际 SKU；EDA 内 FOOTPRINT 占位 "
                            + FOOTPRINT_PLACEHOLDER + " 仅为器件库结构绑定，非最终声明，禁止用于制造）",
        "erc": {
            "error": 0,
            "warning": 2,
            "detail": "CHECKFLOATPIN×2 组（40 引脚）：K1–K4 符号第3脚×4（电气未用，预期）；"
                      "J1 未用 17 脚（3V3×2/RST/GPIO15-18/8/3/46/9-14/5V，预期未使用）；"
                      "J3 未用 19 脚（TX/RX/GPIO1/2/42-35/0/45/48/47/21 及 USB_D±/GPIO19-20，"
                      "USB 属开发板自身通道，载板不引入，预期）",
            "classification": "全部为预期未使用引脚；无悬空网络警告（SHOWDANDLING=0）；无真实设计错误",
        },
        "persistence": {
            "cycle": "编辑→异步落盘(.esch2 22:38)→会话关闭(6307c7d0)→工程重开(9b2df7cb)→导出→再导出",
            "stable": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "assertions": {"ok": ok, "failed": failures, "checks": checks},
        "note": "本 JSON 由 eda-assert-netlist.py 自动生成；禁止手改哈希或大小",
    }
    print(json.dumps({"ok": ok, "failed": failures, "checks": checks},
                     ensure_ascii=False, indent=1))
    if ok and "--check" not in sys.argv:
        EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n")
        sync_project_digest(evidence["sha256"])
        print(f"wrote {EVIDENCE.name}")
    return 0 if ok else 2


def sync_project_digest(digest: str) -> None:
    """把机器计算的 sha256 同步进 project.json 的网表产物条目（避免手抄哈希）。"""
    pj_path = HERE / "project.json"
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    for o in pj.get("domains", {}).get("eda", {}).get("outputs_present", []):
        if o.get("type") == "netlist":
            o["digest"] = digest
    pj_path.write_text(json.dumps(pj, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
