# HachimoDock｜采购执行单（付款之前先完成）

> **2026-11-06：全部尚未下单。** 本页是按上游资料整理的行动清单，参考价格不是实时商家成交价；卖家回复必须保存到你自己的采购日志。买之前先读[步骤 3：购物清单](/projects/hachimodock/03-bom/)和[步骤 4：结构模拟](/projects/hachimodock/04-simulation/)。

**GitHub 进度追踪**：[采购门禁 Issue #1](https://github.com/mayf3/diy-lab/issues/1) · [结构模拟 Issue #2](https://github.com/mayf3/diy-lab/issues/2)。

## Agent-first 采购入口

- [人类制作版](/projects/hachimodock/human-track/)：读者不必自己翻 GitHub、EDA、BOM，也不必有 P1S。只需要提供预算与电脑/加工条件；对精确购物车做最后确认。
- [Agent 执行版](/projects/hachimodock/agent-track/)：Agent 自己检索公开资料、核对型号、做结构模拟、比价并形成可直接购买的 SKU+数量+含运费报价。供应商受登录限制时只请人转发具体截图/询问消息，不交给人作专业兼容判断。
- 现有的卖家问询模板是**Agent 调查受阻后的备用动作**；不能自动表述成新手的必做作业。付款依然须人授权，未拿到证据的核心器件仍 HOLD。

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

> **2026-11-09 研究进展**（研究 Agent 挖透官方固件 BSP + 复刻套件渠道，详见 [research-update-2026-11-09](https://github.com/mayf3/diy-lab/blob/main/source-data/hachimodock/research-update-2026-11-09.md)）：① **屏幕型号锁定 `WLK2802MIPI-15P` / ST7701S**（480×640，MIPI-DSI **1 lane**，800Mbps，官方固件 display.h）——但作者 2026-10-29 评论区说主板用 **22pin** 排线，15P/22P 矛盾成为 BK2/B10 的头号待解问题（要作者或 PCB 实物裁决）。② **最可追溯渠道出现**：[Thorb 复刻套件](https://thorb.com/en/kits/hachimodock-esp32p4-v2)列明该屏（无触摸 ¥75/套装 ¥69；触摸+前壳 ¥78/88），**当前全部缺货**——已加入问询话术⑤。③ **键帽=Choc V1 专用双脚键帽**（PG1350），淘宝"十字1353"可能是 Choc V2/MX 十字杆，**不能按标题买**；海外 PandaKB 有专用页，国内混售未验证。④ 扬声器 B06 退回 HOLD：微雪板载 ES8311+NS4150B，Thorb 整套标 8Ω 1W，原版 2011 SKU 仍未锁定。⑤ 有证据参考小计约 **¥211.73**（不含 PCB 打样/运费/FFC），预算 ¥360 剩余约 ¥148——**条件可行，不可采购确认**。

> **2026-11-06 晚间实查进展**（Brave 打开微雪产品页与立创项目页）：① 微雪产品页和文档**都不公布 silicon 版次**，BK1 只能靠卖家书面确认；产品分 Standard（无排针）/ **With pre-soldered header（预焊排针）** / KIT-A / KIT-B 四档，微雪国际站当日整线显示 Out of Stock（国内渠道另行确认）。② **PCB_V1.2 内嵌 BOM 表实锤：`CPG135001D01 / 封装 KEY-TH_CPG135001D0X / LCSC C400229 ×3`**，原理图 `SCH_V1.2`（创建 2026-07-30，**更新 2026-10-30**）中 SW1/SW2/SW3 符号也明确标注 CPG135001D01——正文"BOX 轴"应视为泛称，**购买以 CPG135001D01 为准**；剩余待办收窄为"键帽与轴体在外壳键孔中的配合"。③ **原作者 2026-10-29 评论区回复**：主板和屏幕通过 **22pin** 排线连接，"买屏的时候得给店家说要 22p 的线；没有就淘宝找 22pin 0.5mm 间距 同向 FFC 线"——该说法与 2026-11-09 固件 BSP 的 15P 证据冲突，以作者/实物裁决为准。④ 原理图更新日期 2026-10-30 晚于评论区答复，说明工程近期有改动，打开工程时若提示网表变更仍**先问作者再动手**。

1. **开发板：** 购买微雪 `ESP32-P4-WIFI6-M`（对应官方型号 SKU **31647**）；向卖家索取实际 ESP32-P4 silicon 版次照片或书面确认，并确认是否焊好两排 20Pin 排针。[微雪文档](https://docs.waveshare.com/ESP32-P4-WIFI6)。**辨别依据（2026-11-06 检索官方资料）**：Espressif 对 ESP32-P4 采用 vM.X 版次命名，v1.x（含 v1.3）与 v3.0+ 是**互斥的固件构建目标**（[版次识别指南](https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32p4/01-chip-identification/index.html)）；微雪官方说明丝印/PCB 版号不等于 silicon 版次，收货后用 `esptool.py --chip esp32p4 -p 端口 chip_id` 不写 flash 直接读出实际版次（[官方辨别文档](https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-X/blob/main/docs/silicon-revisions.md)）——**BK1 的最终证据以实读为准**，卖家答复只是预检。
2. **屏幕：** 请求卖家提供 *具体型号*、**480×640、MIPI-DSI**、背光/触控接口、FFC Pin 数与间距、接点方向、排线长度和外框尺寸。2.8 英寸只是尺寸，不能证明可用。[上游项目](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)。**渠道风险（2026-11-06 检索）**：公开搜索未找到"2.8 寸 480×640 MIPI-DSI 圆形屏"的直接在售商品（电商常见圆屏为 3.4 寸 800×800 / 4 寸）——这块屏**不是标准品**，建议同时向作者交流群或其他复刻者询问实际购买店铺，不要按尺寸关键词盲搜下单。
3. **机械轴：** ~~`PCB_V1.2` BOM 为 `CPG135001D01 / C400229`，但正文出现 BOX 轴描述~~ → **2026-11-06 已确认以 `CPG135001D01`（C400229）×3 为准**（PCB BOM + 原理图双证据）；仍需用 STEP 检查键帽/轴体在外壳键孔的配合，或向复刻者求同版实装证据。[上游 BOM](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)
4. **PCB：** 在嘉立创 EDA 打开 `PCB_V1.2`，核对网络变更提示、轴体封装、两排 20P 排母间距、板厚和连接器位置；**不要点"自动更新 PCB 网络"后直接下单**，先找原作者确认是否以已发布 PCB 文件为准。原理图页可免登录预览（已核对：U1 为 2×20P 连接，SW1-3 = CPG135001D01，摇杆 U2 = YA13S），编辑器内打开需登录立创账号。

这四项同步登记在可下载的[阻塞项登记表](/downloads/hachimodock-blockers.csv)：状态按 `open → asked（已向卖家/作者提问）→ closed（证据齐全）` 推进；改成 `closed` 必须附证据链接和核验日期，`scripts/check.py` 会拒绝没有证据的关闭，四项未全部关闭前项目状态不得标记为“已验证”。

## 可直接查找/询价的入口

- [微雪开发板产品页](https://www.waveshare.com/esp32-p4-wifi6.htm)（选 M，确认不是 DB、Pico 等其他板）。
- [立创 HachimoDock PCB / BOM / STEP / 装配教程](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc)。
- [立创摇杆 C37323748](https://item.szlcsc.com/39051755.html)：`YA13S-L7.4-B10Ka(60)-0-DL01`、插件 14P、22.6×16.7mm。
- [立创轴体型号 C400229](https://www.lcsc.com/product-detail/Mechanical-Keyboard-Shaft_Kailh-CPG135001D01_C400229.html)：**只能用于比对，不能当作已经通过兼容验证的购买推荐。**
- [Github Releases](https://github.com/YizhengWw/HachimoDock/releases/latest)：Mac 客户端和 v1/v3 对应烧录包，不用购买第三方预烧录服务。

## 复制给卖家的信息

**① 微雪（淘宝"微雪旗舰店"或官方店客服）：**

> 你好，我要复刻 HachimoDock 开源项目，需要购买 ESP32-P4-WIFI6 开发板（**预焊排针版**）。下单前请确认三件事：① 现在发货的板子板载 ESP32-P4 芯片是哪个 silicon 版本（chip revision v1 还是 v3）？官方固件区分 v1/v3 两个包，版次发错会烧录失败。② 能否拍一张芯片丝印照片或在订单备注注明版次？③ 你们发货的是 Standard（不带排针）还是 With pre-soldered header（预焊两排 20Pin 排针）版本？我需要预焊排针的。谢谢！

**② 屏幕卖家（2026-11-09 升级：官方固件 BSP 已锁定型号 WLK2802MIPI-15P / ST7701S）：**

> 你好，我在复刻立创开源项目 HachimoDock，主控 ESP32-P4，需要屏幕 **WLK2802MIPI-15P（ST7701S 驱动，2.8 寸 480×640 IPS，MIPI-DSI 1 lane，15P FFC）**。请确认：① 有货吗？是原厂 WLK2802 还是兼容款？② 外形是 2.5D 玻璃曲面圆形屏还是平面屏？发实物照片和外框尺寸图（公开资料约 65×46.2mm，需要同版本实测图）。③ 随屏是否附 **15P FFC** 排线？长度和接点方向（A/B 面）？④ 背光供电电压/电流是否板载限流？⑤ 支持自定义初始化（ST7701S）吗？麻烦发规格书，谢谢！

**③ 轴体卖家（立创商城 C400229 或凯华经销）：**

> 你好，请确认商品：凯华 **CPG135001D01**（LCSC 编号 C400229，即 PG1350 / Choc V1 红轴，插件）。我要买 3 颗装到 PCB 的 KEY-TH_CPG135001D0X 直插封装上。请告知：① 最小包装数量和单价？② 有配套 **Choc V1 专用双脚（two-prong）键帽**吗？注意我不要 MX/BOX 十字杆键帽，也不要 Choc V2/1353。谢谢！

**④ 可选·发给原作者（立创私信或 GitHub）：**

> 你好，我在按 PCB_V1.2 复刻 HachimoDock。三个问题：① SCH_V1.2 原理图更新日期为 2026-10-30，晚于 PCB 发布——在编辑器打开工程若提示网表变更，应以哪份为准？② 固件 BSP 里屏幕目标是 **WLK2802MIPI-15P**（15P FFC），但你 2026-10-29 评论区回复说主板和屏幕用 **22pin** 排线——PCB 端连接器到底是 15P 还是 22P？中间有转接吗？③ 原理图和 PCB BOM 都是 CPG135001D01，教程正文写 BOX 轴，购买按 CPG135001D01（PG1350/Choc V1）对吗？谢谢！

**⑤ Thorb 复刻套件（https://thorb.com/en/kits/hachimodock-esp32p4-v2 ，2026-11-09 页面显示屏幕选项缺货）：**

> 你好，我对 HachimoDock ESP32-P4 V2 复刻套件感兴趣。请告知：① 套件里的屏幕选项（WLK2802MIPI-15P，¥69/75 档）什么时候补货？可以**单独购买屏幕**吗？② 是 V2 版吗？搭配的主控板芯片是 ESP32-P4 v1.x 还是 v3.x silicon？③ 屏幕随附的 15P FFC 长度和接点方向？④ 触摸版用的触摸 IC 型号？⑤ 键帽是 Choc V1 专用双脚款吗？谢谢！

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

**采购准入条件：** 阻塞项登记表中四个 BK 行全部 `closed` 且均有可核验证据，所有主要硬件的型号/接口/结构一致，总价含 PCB、运费、耗材与工具符合自己的预算，才批准批次 C 付款。聊天里的“应该可以”不算通过。

## 出问题怎么办

若卖家只给宣传图不提供规格：继续 HOLD；从官方作者、原厂规格书或已复刻用户那里取得同版本证据。若 EDA 与 BOM 冲突，绝不自作主张更改板子，先按原工程版本提问。若单台 PCB 打样不划算，先询价最小打样数量及运费，不要单纯从展示的片价估算到手价。

**下一阶段**：[打板与 PCB 验收](/projects/hachimodock/05-pcb/) · [进度/失败记录](/projects/hachimodock/13-log/)
