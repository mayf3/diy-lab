# G1 核实：ESP32-S3-DevKitC-1 购买 SKU 核查（2026-11-27）

**状态：官方型号谱系已核实（乐鑫官网当日快照）；国内现货价与预焊排针版本待核实。不构成下单指令，付款由发起人本人执行。**

## 官方在售变体（来源：乐鑫官网产品页，2026-11-27 抓取，HTTP 200）

| 变体 | Flash | PSRAM | 官方列出的渠道 |
| --- | --- | --- | --- |
| ESP32-S3-DevKitC-1-N8R8 | 8 MB | 8 MB | AliExpress |
| ESP32-S3-DevKitC-1-N16R8 | 16 MB | 8 MB | Mouser（+DigiKey 等） |
| ESP32-S3-DevKitC-1U-N8R8 / -U-N16R8 | 同上 | 同上 | 带 U.FL 天线连接器版本 |
| ESP32-S3-DevKitC-1-N32R16V | 32 MB | 16 MB | AliExpress；官方参考价 **$17**（Sample Price for Reference） |

- 官方页面参考价口径：`AliExpress Sample Price for Reference`——**是参考价，不是实时成交价**。
- 旧 N8R2 档在当前官方 S3-DevKitC-1 列表中已不出现（仅 S2-DevKitC-1-N8R2 出现）——按官网现状选型。
- 板上双 USB（USB-OTG + UART 桥）与 J1/J3 2×22P 排针事实沿用 [interface-contract.md](interface-contract.md)（官方 PDF 依据）；v1.1 版次标记以到货实物丝印为准。

## R1 选型建议（待发起人确认）

**推荐目标：ESP32-S3-DevKitC-1-N8R8（无 U.FL 版）**——四键 USB HID 的 Flash/PSRAM 用量极小，
8+8 MB 富余；比 N16R8 更易得（AliExpress 主渠道）且价格更低。N16R8 仅在 N8R8 缺货时备选。

## 下单前必须核实（逐项打勾后才可付款）

1. **预焊排针**：商品页/卖家确认 J1/J3 排针已焊（R1 载板按排针插接设计）；未焊版需自焊，装配计划要改。
2. **版次丝印**：到货后核对板上 `ESP32-S3-DevKitC-1 v1.1`（或更新）丝印与 [interface-contract.md](interface-contract.md) 引脚表一致。
3. **双 USB 实物间距与朝向**：载板双 USB 开孔（G2-2）按实物测量后定稿，不用网页图比例。
4. **国内渠道现价**：乐鑫淘宝官方店/微雪/立创商城现货价与运费（元元件库或卖家页恢复后回填本表）。

## 与版本合同的关系

本文属于 R1 选型资料，不产生冻结；选定并到货验收后才把 DevKitC SKU 写入 BOM（G6 冻结范围）。
