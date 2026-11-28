#!/usr/bin/env python3
"""网表 ERC v2 负向测试集：每条规则必须证明能拒绝对应的真实错误。

方法：深拷贝基线器件表 → 注入变异（对应 P0-1/2/3 与系统性规则的错误形态）→
断言 ERC 报出预期错误。这是「检查器检查的是真实电气结构」的证据之一。

运行：python3 source-data/christmas-buddy/eda/netlist_tests.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import netlist as NL  # noqa: E402

def mutated(fn):
    """拷贝基线，应用变异，返回 (nets, attrs, devices)。"""
    devices = copy.deepcopy(NL.DEVICES)
    fn(devices)
    nets = NL.build_nets(devices)
    return nets, copy.deepcopy(NL.NET_ATTR), devices

def set_pin(devices, ref, pin, **kw):
    for d in devices:
        if d["ref"] == ref and pin in d["pins"]:
            d["pins"][pin].update(kw)
            return
    raise KeyError(f"{ref}.{pin}")

def drop_device(devices, ref):
    devices[:] = [d for d in devices if d["ref"] != ref]

CASES = [
    ("T1 基线（应 0 错误）", lambda d: None, None),

    ("T1n P0-1 类：R_EN 上拉回 5V_MAIN 应被拒",
     lambda d: set_pin(d, "R_EN", "1", net="5V_MAIN", vdom="5V"),
     "P0-1 类"),

    ("T2n P0-2 类：删除 R_MODE（BCM25 直连 AMP_SD）应被拒",
     lambda d: (set_pin(d, "U1", "BCM25", net="AMP_SD"), drop_device(d, "R_MODE")),
     "P0-2 类"),

    ("T3n P0-3 类：U6 DIR 接 GND 应被拒",
     lambda d: set_pin(d, "U6", "DIR", net="GND", vdom="0V"),
     "P0-3 类"),

    ("T4n LED：右眼 DIN 并联回链级0（破坏菊花链）应被拒",
     lambda d: set_pin(d, "J6", "3", net="LED_DIN"),
     "LED_CHAIN1"),

    ("T5n I2S：BCLK 出现第二驱动应被拒",
     lambda d: d[3]["pins"].update({  # U2 追加第二个 BCLK 驱动源
         "BCLK2": NL.P("BCLK2", "I2S_PCM_CLK", "OUT", "3V3")}),
     "I2S_PCM_CLK"),

    ("T6n CC：删除 R_CC2 应被拒",
     lambda d: drop_device(d, "R_CC2"),
     "CC2_RD"),

    ("T7n 保护：TVS 换 3V 型（standoff<5V）应被拒",
     lambda d: (lambda dd: [x["attrs"].update({"tvs_standoff_v": 3.0}) for x in dd if x["ref"] == "D1"])(d),
     "TVS"),

    ("T8n 焊桥：S1/S2 同方案归属应被拒",
     lambda d: set_pin(d, "U1", "BCM10", net="LED_PI"),  # no-op 变量保持结构
     None),
]

def case8_bridge_conflict(d):
    for x in d:
        if x["ref"] == "S2":
            x["attrs"]["closed_in"] = "A"
CASES[7] = ("T8n 焊桥：S1/S2 同方案归属应被拒", case8_bridge_conflict, "焊桥组")

def main() -> None:
    ok = True
    print("=== 网表 ERC v2 负向测试 ===")
    for name, fn, expect in CASES:
        nets, attrs, devices = mutated(fn)
        _, errors, _ = NL.run_erc(nets, attrs, devices)
        if expect is None:
            passed = len(errors) == 0
            detail = f"errors={len(errors)}"
        else:
            passed = any(expect in e for e in errors)
            detail = next((e for e in errors if expect in e), f"未触发（共 {len(errors)} 条错误）")
        print(f"  [{'PASS' if passed else 'FAIL'}] {name} — {detail[:110]}")
        ok = ok and passed

    # 正向量化：AMP_SD 仲裁数值表（与 netlist.json cases 一致）
    v_high = 3.3 * 100 / (620 + 100)
    i_force = 3.3 / 620_000
    print("\n=== AMP_SD 仲裁数值 ===")
    print(f"  Pi 高：V_SD = {v_high:.3f}V ∈ (0.16, 0.77) → (L+R)/2 模式：{'PASS' if 0.16 < v_high < 0.77 else 'FAIL'}")
    print(f"  ESP32 强制时 Pi 灌入电流 = {i_force*1e6:.1f}µA（无应力阈值 1mA）：{'PASS' if i_force < 1e-3 else 'FAIL'}")
    rpd_ok = all(0.16 < 3.3 * rpd / (620 + rpd) < 0.77 for rpd in (92, 108))
    print(f"  RPD 容差角 92–108kΩ 下仍在 (L+R)/2 带：{'PASS' if rpd_ok else 'FAIL'}")
    rc_ms = 10_000 * 1e-6 * 1000
    print(f"  ESP32 EN RC = {rc_ms:.0f}ms > tH 3ms：{'PASS' if rc_ms > 3 else 'FAIL'}")
    ok = ok and (0.16 < v_high < 0.77) and (i_force < 1e-3) and rpd_ok and rc_ms > 3

    print("\n结果:", "ALL PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
