# Christmas Buddy V1 · 网表级原理图 ERC v2 报告

日期：2026-11-28｜器件 38，网络 54

## 数据手册事实（官方 PDF 本地提取，2026-11-28）

- **esp32_en**：ESP32-S3 WROOM-1 Datasheet §Pin Definitions: EN High=on/Low=off，不得悬空；§DC Characteristics: VIH=0.75×VDD1，绝对上限 VDD1+0.3V；§Strapping: tSU=0ms/tH=3ms
- **max98357_sd**：MAX98357A Datasheet §SD_MODE and shutdown operation: 内部 RPD 92–108kΩ；RLARGE(kΩ)=222.2×VDDIO−100 → (L+R)/2 模式，VDDIO=3.3V → 633.3kΩ；比较点 B0=0.16V/B1=0.77V/B2=1.4V (typ)；GAIN_SLOT=GND→+12dB（官方正文）
- **lvc1t45**：TI SCES515N: DIR=L: B→A / DIR=H: A→B；DIR 参考 VCCA，VIH(DIR)=2V@3–3.6V；VCC isolation：任一 VCC=GND 两端口高阻

## P0 修复摘要

- P0-1：R_EN 上拉 5V_MAIN→3V3_MCU，新增 C_EN 1µF（RC=10ms>tH 3ms）
- P0-2：AMP_SD 仲裁重构——删除外置下拉（保留官方内部 100k），BCM25 经 R_MODE 620k 隔离，Q1 强制静音与 Pi 高电平争用电流仅 5.3µA；(L+R)/2 单声道模式由阻值编码实现
- P0-3：U6 DIR GND→VCCA（官方功能表 DIR=H: A→B）

## ERC 结果

- 全部通过（0 error, 0 warning）
