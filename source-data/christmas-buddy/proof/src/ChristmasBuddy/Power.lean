/-!
# Christmas Buddy V1 · M1 电源预算关键约束

数值与 `power/budget.json`（M1 数值基线，2026-11-28）一致；改预算必须同步改这里并重跑证明。

证明的性质：
- `thm_magic_within_adapter`：常规最坏场景（Magic 灯效并发）×1.5 裕量仍在外置 5V/3A 适配器内。
- `thm_worst_within_adapter`：设计最坏并发（全白灯+满音量+满载）≤ 适配器 3A。
- `thm_led_capped_rail`：LED 软帽（60% 占空）后最坏电流 ≤ LED 独立轨 1.6A。
- `thm_rail_sum_bound`：通用引理——各域负载不超各自预算则总负载不超总预算。
- `thm_3v3_rail`：ESP32 TX 峰值 + 麦克风 + 杂项 ≤ 3V3 轨 500mA 设计容量。

环境假设：
- ASM-P1：适配器为合规 5V/3A 认证电源（实物验收时核对铭牌）。
- ASM-P2：budget.json 中各模块电流为其数据手册最大值或保守估计。
-/

namespace ChristmasBuddy.Power

/-- 常规最坏场景（Magic）总电流 mA（budget.json `magic` 场景）。 -/
def magicWorst : Nat := 1126

/-- 设计最坏并发 mA（budget.json `worst_case` 场景）。 -/
def worstAll : Nat := 2513

/-- 外置适配器容量 mA。 -/
def adapterCap : Nat := 3000

/-- LED 独立轨容量 mA。 -/
def ledRail : Nat := 1600

/-- LED 全白数据手册最坏 mA（22 颗 × 60mA）。 -/
def ledWorst : Nat := 1320

/-- 3V3 轨容量 mA（ESP32 官方建议设计值）。 -/
def v33Rail : Nat := 500

/-- ESP32 TX 峰值 mA。 -/
def espPeak : Nat := 345

/-- 麦克风 mA。 -/
def micMa : Nat := 2

/-- 杂项 mA。 -/
def miscMa : Nat := 5

/-- 常规最坏 ×1.5 裕量（整数运算：×3 再 /2）。 -/
theorem thm_magic_within_adapter : magicWorst * 3 / 2 ≤ adapterCap := by decide

/-- 设计最坏并发 ≤ 适配器容量（此场景余量为 0，由 M2 帽策略禁止常规触发）。 -/
theorem thm_worst_within_adapter : worstAll ≤ adapterCap := by decide

/-- LED 软帽 60% 后 ≤ LED 轨容量。 -/
theorem thm_led_capped_rail : ledWorst * 3 / 5 ≤ ledRail := by decide

/-- LED 轨容量也覆盖不设帽的最坏（硬件兜底不烧毁）。 -/
theorem thm_led_rail_covers_uncapped : ledWorst ≤ ledRail := by decide

/-- 通用引理：各域电流分别不超各自预算，则总电流不超预算之和。 -/
theorem thm_rail_sum_bound {a b c d capA capB capC capD : Nat}
    (ha : a ≤ capA) (hb : b ≤ capB) (hc : c ≤ capC) (hd : d ≤ capD) :
    a + b + c + d ≤ capA + capB + capC + capD := by omega

/-- 3V3 轨覆盖 ESP32 峰值 + 麦克风 + 杂项。 -/
theorem thm_3v3_rail : espPeak + micMa + miscMa ≤ v33Rail := by decide

/-- 待实测轮解除的义务（UNPROVEN 义务登记）：Pi 实测峰值 ≤ 预算 520mA。
    该量在实物测试轮以实测观察解除；在证明体系中显式保持未证。 -/
theorem thm_pi_measured_peak_obligation (piMeasured : Nat) (h : piMeasured ≤ 520) :
    piMeasured ≤ 520 := h

end ChristmasBuddy.Power
