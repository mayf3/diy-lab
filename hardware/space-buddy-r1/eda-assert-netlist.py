#!/usr/bin/env python3
"""Space Buddy R1 · 网表机器断言（唯一源 = 真实导出的 PROTEL 网表 .net 文件）。

用法：
    python3 eda-assert-netlist.py                        # 断言 + 重新生成 netlist-evidence.json
    python3 eda-assert-netlist.py --check                # 只断言，不写任何文件（校验器/CI 调用）
    python3 eda-assert-netlist.py --check --net X --json Y  # 指定沙箱路径（负向测试用）

规则（2026-11-28 隔离轮验收）：
  1. GPIO4={J1-4,K1-1} GPIO5={J1-5,K2-1} GPIO6={J1-6,K3-1} GPIO7={J1-7,K4-1}
  2. GND = 四开关接地端 + 真实开发板 GND 排针（J1-22, J3-1, J3-21, J3-22）
  3. 四路 GPIO 唯一映射，无互短（任一引脚不得出现在两个网络）
  4. 无电源短路（3V3/5V 等电源网络/引脚不得出现）
  5. 开关引脚语义：K1–K4 只有电气脚 1/2（MX 轴=2 金属触点；塑料定位脚不得成为第 3 电气脚）
  6. 排母实际引脚已进入网络（非仅有标签的假完成）
  7. 占位隔离（不可仅靠文字声明）：
     - C9900017374 在整份网表中不得出现
     - K1–K4 Add into BOM = no（BOM 真实导出无开关行）
     - K1–K4 Convert to PCB = no（错误占位封装无法进入 PCB）
     - K1–K4 Supplier Part = TBD-MECH-AXIS
  8. 连接器：J1/J3 Supplier Part = C18078140；器件名 = BX-PM2.54-1-22PY
     （1×22P / 2.54mm / PM 母排）；整份网表不得出现 KH-2.54PH90 公排针
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GPIO_EXPECT = {
    "GPIO4": {"J1-4", "K1-1"},
    "GPIO5": {"J1-5", "K2-1"},
    "GPIO6": {"J1-6", "K3-1"},
    "GPIO7": {"J1-7", "K4-1"},
}
GND_EXPECT = {"K1-2", "K2-2", "K3-2", "K4-2", "J1-22", "J3-1", "J3-21", "J3-22"}
POWER_NETS = {"3V3", "3V3_1", "5V", "VCC", "VIN"}
POWER_PIN_SIGNS = ("3V3", "5V", "VCC", "VIN")

FORBIDDEN_SUBSTRINGS = (
    "C9900017374",   # 错误的 4.5×4.5 SMD 轻触开关占位——整份网表禁入
    "KH-2.54PH90",   # 公排针——只允许母排（BX-PM2.54-1-22PY）
)
SWITCH_DESIGNS = ("K1", "K2", "K3", "K4")
SWITCH_PINS_ALLOWED = {"1", "2"}   # MX 机械轴=两电气触点；塑料定位脚不是电气引脚
SWITCH_SUPPLIER_PART = "TBD-MECH-AXIS"
CONN_SUPPLIER_PART = "C18078140"
CONN_PARTNAME = "BX-PM2.54-1-22PY"


def parse_protel(text: str) -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    """解析 PROTEL 2.0：返回 (nets {name: [designator-pin]}, components {des: fields})。"""
    text = text.replace("\r\n", "\n")
    nets: dict[str, list[str]] = {}
    comps: dict[str, dict[str, str]] = {}
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


def run_assertions(text: str) -> tuple[bool, list[str], dict[str, str]]:
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

    # 3. 唯一映射 / 无互短
    pin_owner: dict[str, list[str]] = {}
    for name, pins in nets.items():
        for p in pins:
            pin_owner.setdefault(p, []).append(name)
    multi = {p: ns for p, ns in pin_owner.items() if len(ns) > 1}
    expect(not multi, "无引脚跨网络互短")

    # 4. 无电源短路
    for bad in POWER_NETS:
        expect(bad not in nets, f"不存在电源网络 {bad}")
    for name in ("GPIO4", "GPIO5", "GPIO6", "GPIO7", "GND"):
        for p in nets.get(name, []):
            expect(not any(s in p for s in POWER_PIN_SIGNS), f"{name} 不含电源引脚 {p}")

    # 5. 开关两电气脚语义（pin3 不得存在；每键 1/2 两脚均在网）
    for k in SWITCH_DESIGNS:
        expect(f"{k}-1" in pin_owner and f"{k}-2" in pin_owner, f"{k} pin1/pin2 均入网")
    all_pins = set(pin_owner)
    for k in SWITCH_DESIGNS:
        stray = [p for p in all_pins if p.startswith(k + "-") and p not in (f"{k}-1", f"{k}-2")]
        expect(not stray, f"{k} 无第三电气脚（塑料定位脚不入网表）")

    # 6. 排母实际引脚入网（假完成检测）
    for net, want in GPIO_EXPECT.items():
        got = set(nets.get(net, []))
        expect(bool(got) and got == want, f"{net} 排母引脚真实入网（非仅标签）")

    # 7. 占位隔离——语义强制，非文字声明
    expect(not any(s in text for s in FORBIDDEN_SUBSTRINGS[:1]),
           "整份网表不含 C9900017374")
    for k in SWITCH_DESIGNS:
        f = comps.get(k)
        expect(f is not None, f"{k} 在网表器件表中")
        if f:
            expect(f.get("Add into BOM", "").lower() == "no", f"{k} Add into BOM=no")
            expect(f.get("Convert to PCB", "").lower() == "no", f"{k} Convert to PCB=no")
            expect(f.get("Supplier Part", "") == SWITCH_SUPPLIER_PART,
                   f"{k} Supplier Part={SWITCH_SUPPLIER_PART}")

    # 8. 连接器身份与公排针禁入
    for j in ("J1", "J3"):
        f = comps.get(j)
        expect(f is not None, f"{j} 在网表器件表中")
        if f:
            expect(f.get("Supplier Part", "") == CONN_SUPPLIER_PART,
                   f"{j} Supplier Part={CONN_SUPPLIER_PART}")
            expect(f.get("PARTTYPE", "") == CONN_PARTNAME,
                   f"{j} 器件名={CONN_PARTNAME}（1×22P/2.54mm 母排）")
    expect(FORBIDDEN_SUBSTRINGS[1] not in text, "整份网表不含 KH-2.54PH90 公排针")

    ok = not failures
    return ok, failures, checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只断言，不写文件")
    ap.add_argument("--net", default=str(HERE / "netlist-evidence.net"))
    ap.add_argument("--json", default=str(HERE / "netlist-evidence.json"))
    args = ap.parse_args()
    net_path = Path(args.net)
    ev_path = Path(args.json)

    raw = net_path.read_bytes()
    text = raw.decode("utf-8")
    _, comps = parse_protel(text)
    ok, failures, checks = run_assertions(text)

    if args.check:
        print(json.dumps({"ok": ok, "failed": failures}, ensure_ascii=False, indent=1))
        return 0 if ok else 2

    nets, _ = parse_protel(text)
    evidence = {
        "format": "PROTEL NETLIST 2.0",
        "exported_at": "2026-11-28",
        "source": "eda.sch_ManufactureData.getNetlistFile('space-buddy-r1','Protel2') 真实导出（非手写）",
        "session": "626b439c (headless，保存→关闭→重开后稳定导出)",
        "project_uuid": "4ab9e52666a4fc7fe9b1d0c7c4c4263444d972eb139973d04478d976200a78b8",
        "schematic_uuid": "7415725566084bd0",
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "nets": {k: sorted(v) for k, v in nets.items()},
        "components": {k: {"footprint_declared": v.get("FOOTPRINT", ""),
                            "supplier_part": v.get("Supplier Part", ""),
                            "partname": v.get("PARTTYPE", ""),
                            "add_into_bom": v.get("Add into BOM", ""),
                            "convert_to_pcb": v.get("Convert to PCB", "")}
                        for k, v in sorted(comps.items())},
        "switch_symbol": "两电气脚常开（YD-3410 器件承载通用开关符号，pin1/pin2；"
                         "MX 机械轴=2 金属触点，塑料定位脚不属于电气引脚）",
        "switch_footprint": "TBD（样轴确认后绑定 Boba U4 或实际 SKU 准确封装）。"
                            "EDA 占位绑定 SW-SMD_L3.9-W2.9-LS4.8-EH-A 已被 Convert to PCB=no 语义隔离："
                            "无法进入 PCB；Add into BOM=no 隔离：无法进入 BOM（BOM 真实导出仅 J1,J3 一行）",
        "bom_export": {"rows": [{"designator": "J1,J3", "part": "BX-PM2.54-1-22PY",
                                  "supplier_part": "C18078140"}],
                        "switch_present": False},
        "erc": {
            "error": 0,
            "warning": 2,
            "detail": "CHECKFLOATPIN×2 组（36 引脚，全部=排母预期未使用引脚）："
                      "J1 未用 17 脚（3V3×2/RST/GPIO15-18/8/3/46/9-14/5V）；"
                      "J3 未用 19 脚（TX/RX/GPIO1/2/42-35/0/45/48/47/21 及 USB_D±/GPIO19-20，"
                      "USB 属开发板自身通道，载板不引入）。开关第 3 脚浮动警告已随两脚符号更换消失",
            "classification": "全部为预期未使用引脚；无悬空网络警告（SHOWDANDLING=0）；无真实设计错误",
        },
        "persistence": {
            "cycle": "换件+属性隔离→异步落盘→会话关闭→工程重开→导出→再导出逐字节一致（d3f46041…）",
            "stable": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "caveat": "关闭前导出捕获属性异步落盘中间态（fbaa5030…），以重开稳定导出为唯一源",
        },
        "assertions": {"ok": ok, "failed": failures},
        "note": "本 JSON 由 eda-assert-netlist.py 自动生成；禁止手改哈希或大小",
    }
    print(json.dumps({"ok": ok, "failed": failures}, ensure_ascii=False, indent=1))
    if ok:
        ev_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=1) + "\n")
        sync_project_digest(evidence["sha256"])
        print(f"wrote {ev_path.name}")
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
