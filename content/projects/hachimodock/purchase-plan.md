# HachimoDock｜采购执行单（付款之前先完成）

> **2026-11-06：全部尚未下单。** 本页是按上游资料整理的行动清单，参考价格不是实时商家成交价；卖家回复必须保存到你自己的采购日志。买之前先读[步骤 3：购物清单](/projects/hachimodock/03-bom/)和[步骤 4：结构模拟](/projects/hachimodock/04-simulation/)。

**GitHub 进度追踪**：[采购门禁 Issue #1](https://github.com/mayf3/diy-lab/issues/1) · [结构模拟 Issue #2](https://github.com/mayf3/diy-lab/issues/2)。

## 目标

把**想买什么、找谁核实、何时付款**拆成三个独立动作。你不需要先学完电子工程，也不必为了赶进度把所有东西一次下单。

## 分批采购建议

| 批次 | 项目 | 现在是否建议付款 | 为什么 |
| --- | --- | --- | --- |
| 0：免费 | 下载 STEP、PCB、BOM、装配视频；安装 FreeCAD、Bambu Studio | 不用付钱 | 先知道模型是否装得下 |
| A：询价 | ESP32-P4-WIFI6-M、2.8" MIPI-DSI 屏+FFC、3 个轴体、PCB_V1.2 打样 | **仅询价，不付款** | 四项互相约束，型号不清会连锁返工 |
| B：已知标准件 | 2×20P 排母、M2.5 螺钉/铜螺母、USB 线、通孔练习板 | **确认规格后可买** | 不涉及决定性屏幕兼容，但仍需看数量和运输成本 |
| C：正式制作 | 主控、屏幕、匹配排线、PCB、轴体、摇杆、喇叭与配件 | **A 的证据齐全后再付款** | 需要确保所有零件能组合，避免买错导致退换 |

## 四个需要关闭的采购阻塞项

1. **开发板：** 购买微雪 `ESP32-P4-WIFI6-M`（对应官方型号 SKU **31647**）；向卖家索取实际 ESP32-P4 silicon 版次照片或书面确认，并确认是否焊好两排 20Pin 排针。[微雪文档](https://docs.waveshare.com/ESP32-P4-WIFI6)
2. **屏幕：** 请求卖家提供 *具体型号*、**480×640、MIPI-DSI**、背光/触控接口、FFC Pin 数与间距、接点方向、排线长度和外框尺寸。2.8 英寸只是尺寸，不能证明可用。[上游项目](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)
3. **机械轴：** `PCB_V1.2` BOM 为 `CPG135001D01 / C400229`，但正文出现 BOX 轴描述。应先用 EDA 预览焊盘和实际 3D 外壳配合，向作者/复刻者求同版实装证据。[上游 BOM](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)
4. **PCB：** 在嘉立创 EDA 打开 `PCB_V1.2`，核对网络变更提示、轴体封装、两排 20P 排母间距、板厚和连接器位置；**不要点“自动更新 PCB 网络”后直接下单**，先找原作者确认是否以已发布 PCB 文件为准。

## 可直接查找/询价的入口

- [微雪开发板产品页](https://www.waveshare.com/esp32-p4-wifi6.htm)（选 M，确认不是 DB、Pico 等其他板）。
- [立创 HachimoDock PCB / BOM / STEP / 装配教程](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)。
- [立创摇杆 C37323748](https://item.szlcsc.com/39051755.html)：`YA13S-L7.4-B10Ka(60)-0-DL01`、插件 14P、22.6×16.7mm。
- [立创轴体型号 C400229](https://www.lcsc.com/product-detail/Mechanical-Keyboard-Shaft_Kailh-CPG135001D01_C400229.html)：**只能用于比对，不能当作已经通过兼容验证的购买推荐。**
- [Github Releases](https://github.com/YizhengWw/HachimoDock/releases/latest)：Mac 客户端和 v1/v3 对应烧录包，不用购买第三方预烧录服务。

## 复制给卖家的信息

> 你好，我在复刻 HachimoDock 哈基米机，用微雪 ESP32-P4-WIFI6-M + 官方 PCB_V1.2。请给我这件商品的**实物型号、尺寸图、接口/排线引脚定义与随箱附件**。如果是开发板，请注明实际 ESP32-P4 silicon v1/v3；如果是屏幕，请注明 MIPI-DSI、FFC Pin 数/间距/方向与是否已经在这套板卡上实测；如果是机械轴，请确认能插入 PCB_V1.2 且符合外壳键帽高度。麻烦提供商品规格书或已装配实拍。仅显示尺寸相同不能作为兼容证明，谢谢。

## 采购账本怎么记

先打开[可编辑 BOM CSV](/downloads/hachimodock-bom.csv)，对每一行补：商家、商品精确链接或 SKU、询价日期、含运费到手价、截图证据、数量、收货日期。官方网页参考价和你的实际付款金额必须分列，不要互相覆盖。阶段从 `HOLD → CHECK → ORDERED → RECEIVED → VERIFIED` 逐个推进，前两个阶段尚未购买。

### 建议的本周动作

- [ ] 保存 STEP、PCB 与装配视频到本地（仅自用，不直接复制上游文件到公共 GitHub）。
- [ ] 在 Mac 上检查两份 STEP 与 PCB 的 3D 预览，写下尺寸冲突清单。
- [ ] 向微雪商家发芯片版次问题并保存答复。
- [ ] 向屏幕供应商发完整模组和排线规格问题并保存答复。
- [ ] 在立创 PCB_V1.2 中核实按键轴封装和主控连接尺寸。
- [ ] 从实际购物车导出含运费报价，形成「买/暂缓」决策。

## 验收

**采购准入条件：** 四个阻塞项均有可核验证据，所有主要硬件的型号/接口/结构一致，总价含 PCB、运费、耗材与工具符合自己的预算，才批准批次 C 付款。聊天里的“应该可以”不算通过。

## 出问题怎么办

若卖家只给宣传图不提供规格：继续 HOLD；从官方作者、原厂规格书或已复刻用户那里取得同版本证据。若 EDA 与 BOM 冲突，绝不自作主张更改板子，先按原工程版本提问。若单台 PCB 打样不划算，先询价最小打样数量及运费，不要单纯从展示的片价估算到手价。

**下一阶段**：[打板与 PCB 验收](/projects/hachimodock/05-pcb/) · [进度/失败记录](/projects/hachimodock/13-log/)
