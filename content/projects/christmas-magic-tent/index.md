# Project Christmas Magic Tent｜圣诞互动帐篷


## 目标效果｜圣诞树魔法小屋（2D+3D）

<a class="img-zoom" href="../../media/christmas-magic-tent/concept/christmas-magic-tent-concept-full.png" title="点击放大查看 1536×1024 高清原图"><img src="../../media/christmas-magic-tent/concept/christmas-magic-tent-concept.webp" alt="圣诞树魔法小屋概念效果图（目标设计，非实拍）" loading="lazy"></a>

[放大查看高清原图](/media/christmas-magic-tent/concept/christmas-magic-tent-concept-full.png) · [8步制作路线](/projects/christmas-magic-tent/mixed-media-plan/) · 效果图加入于 2026-11-12

> 这是概念效果图而非实拍。施工时以165cm实木杆款为基础，所有2D+3D装饰固定在可拆独立背板上，电子件和灯串与帐篷结构物理分离。


> **帐篷已购买（2026-11-13 确认；订单截图待回填），尺寸待实测、到货验收未开始。** 目标预算 **≤¥500**。最终 SKU 决策：天猫哎哟宝贝 165cm 实木杆款（READY_BUY→已购，见[采购合并清单](/projects/christmas-magic-tent/consolidated-purchase-plan/)）；历史候选 HelloKitty ¥299.52 **已作废**。当前装饰、图案与结构件仍是设计目标，未打印、未试装。最终 SKU 决策：天猫哎哟宝贝 165cm 实木杆款 **¥210**（READY_BUY，见[采购合并清单](/projects/christmas-magic-tent/consolidated-purchase-plan/)）；历史候选 HelloKitty ¥299.52 **已作废**。当前尺寸、材料、电路仍是设计候选值与模拟结论，非实物结论。

## V1 制作路线（主入口）

**V1 范围**：已选帐篷 + 2D A4 拼接圣诞树图案 + P1S 3D 立体装饰件 + 独立免焊 WLED 可编程灯光。PIR 与 DFPlayer 列入 V2，不阻塞 V1；独立桌面小树（tree-v1）是另一件装置，不承担帐篷装饰。

**→ [开始跟做：V1 制作路线全教程](/projects/christmas-magic-tent/v1-build-guide/)**（含每步的拿什么/做什么/看到什么/失败怎么办）

配套入口：[8 步总览](/projects/christmas-magic-tent/mixed-media-plan/) · [V1 统一 BOM（含与原 ¥423.53 购物车的差异）](https://github.com/mayf3/diy-lab/blob/main/source-data/christmas-magic-tent/v1/v1_wled_bom.csv) · [A4 模板与 STL 生成器](https://github.com/mayf3/diy-lab/tree/main/source-data/christmas-magic-tent/v1) · [WLED 预设](https://github.com/mayf3/diy-lab/blob/main/source-data/christmas-magic-tent/v1/wled_presets.json)

**造型已定**：帐篷旁圣诞树两方案对比与推荐（平面骨架树 25 件/16 螺丝）见 [圣诞树双方案对比](/projects/christmas-magic-tent/tree-designs/)——含效果图、爆炸图、首盘试件清单。

**当前状态**：待下单 → 到货验收 → 按教程第 1 步量尺。权威关卡状态：`source-data/christmas-magic-tent/workflow.json`（9 关，observed 均带证据）。

## 希望实现的四层体验

1. **帐篷结构**：偏向小屋 / 城堡式，可拆搭、可存放的软布空间。
2. **灯光**：**V1 = WLED 可编程灯串（免焊、软件切场景）**；装饰灯主题可换。
3. **传感器**（V2 暂缓，不阻塞 V1）：使用 **HC-SR501 PIR** 检测有人经过或进入（不用于儿童安全监控）。
4. **声音**（V2 暂缓，不阻塞 V1）：Arduino + **DFPlayer Mini** 播放问候声或圣诞音效。

## 已记录但尚未冻结的候选尺寸

| 部位 | 方案尺寸 | 处理方式 |
| --- | --- | --- |
| 小屋总体 | 约 **160 × 110 × 135cm**（长 × 宽 × 高，方案） | 需要先建模，不能直接按这个裁布 |
| 墙体 | 高约 **80cm** | 根据顶棚坡度和儿童站立空间调整 |
| 正面窗 | 约 **40 × 45cm** | 需核对开窗位置与边缘加固 |
| 侧窗 | 约 **30 × 40cm** | 需考虑通风和防夹手 |
| 主体布料 | 曾估算 **6.5–9.5m** | 仅为历史粗估，需以裁片排料重算 |
| 可用空间 | 曾报告宽和进深各 **1000cm** | 作为输入记录，实际安装净空仍需复测 |

主要资源：Bambu P1S、2D 打印机、Arduino UNO R3（2026-11-09 家庭库存盘点确认）。可复用万圣节项目中的布艺、魔术贴和 3D 打印经验。

## 历史研究与决策记录（次级入口）

以下章节保留自模拟与采购研究阶段（2026-11-06 至 11-12），供追溯与审计；**当前口径以页首状态块与 V1 制作路线为准**。权威关卡与验收状态以 `source-data/christmas-magic-tent/workflow.json` 为准。

## 先模拟，不购物：第一阶段任务

1. 用 Blender/FreeCAD 建立参数变量 `length=1600mm`、`width=1100mm`、`ridge_height=1350mm`、`wall_height=800mm`；窗户作为可切换的参考体。
2. 对比门口方向、屋脊净空、儿童进入路径、通风位置、室内取放空间及骨架收纳长度。
3. 从三维模型导出裁片面积和骨架长度估算；打印 **1:5 连接件/小样**，先观察形变，不用估计材料强度代替实测。
4. 先在桌面使用低压供电连接 LED、HC-SR501 和 DFPlayer Mini；确认电源电压、引脚及实际 Arduino 型号，**不得直接接家用市电或让电线暴露在儿童可触区域**。
5. 形成可采购 BOM：确定单根杆、布料长度、供电方式、线材、接头及运费；合计控制在 ¥500 内后才允许下单。

## 项目关卡

- [x] Blender 参数化尺寸模型与可重复修改的源文件保存。**（G0 数字模拟完成，2026-11-06，见 [G0 评审](/projects/christmas-magic-tent/g0-review/)；非实物验证）**
- [x] 帐篷入口、窗户、骨架、布料裁片有完成检查截图。**（G0 几何检查截图与 A/B 对比已完成；裁片为估算，未实测）**
- [ ] 1:5 骨架、连接件与缝制样片已实测。
- [ ] Arduino 型号、低压电源与接线图实际确认。
- [ ] PIR 与 DFPlayer 单独通电测试通过。
- [ ] 安全检查、预算、运费和儿童可达区域问题关闭后，再下单。

本项目与 HachimoDock 不同：**HachimoDock 优先照官方成熟设计复刻，帐篷先做参数化设计与电路原型**。

## 当前进展（2026-11-06）：G0 数字模拟完成

Blender 参数化模型已建成，A（110×160）/ B（160×110）两候选完成几何对比，**仍是数字模拟证据，未采购、未制作实体**：

- **门洞×屋顶冲突验证**：门高 90cm > 檐高 80cm，门洞上角切入山墙；A 净空 10.0cm、B 20.9cm，均通过但 A 余量偏紧。
- **站立净空限制**：两方案仅屋脊下 30cm / 43.6cm 窄条可直立（110cm 儿童），帐内活动以跪坐为主。
- **小可用区域压力测试**：3.0×3.5m 放得下帐篷，但房间门扇范围与门口通道重叠——真实房间复核时“门扇动线”是第一失效点。
- **电子外置决策**：控制盒/电源/扬声器帐外，帐内只留低压发光件；隐藏电子层后基础小屋完整。

详见 **[G0 数字模拟评审](/projects/christmas-magic-tent/g0-review/)**；模型与数据在 `source-data/christmas-magic-tent/g0/`，渲染图在 `public/media/christmas-magic-tent/g0/`。下一步：按 G0 清单向 2–3 款真实商品索要尺寸，回填参数重跑后再决定购买。

## G1 第一轮商品搜寻结果（2026-11-06，公开信息检索，0 PASS，已复核）

按搜寻需求书完成淘宝/京东/宜家/拼多多公开信息检索，**合格候选 0**：商品页普遍只给外廓 W/D/H，**不发布檐口高与门净宽×高**（明细见 `source-data/christmas-magic-tent/candidates.md`）。人工复核后修正两条记录：

- **HelloKitty 游戏屋（160×100×130 加长版）**：早前记录的"16mm 金属支架"实际对应 130×100×130 中号款，**加长版杆径恢复为待核实**，必须按具体商家 SKU 重新核实。
- **宜家 HÖVLIG（¥199，120×120×164）降级为"仅尺寸/结构参考，非采购目标"**：官方页面明确警告**不要在帐篷内外悬挂灯串、装饰品，以免孩子被绊住**——与本项目"星星灯+装饰+帐篷"的核心方案直接冲突。不再建议线下专程测量。

**策略（G1 拆分为两子阶段，详见 `sourcing-brief.md` v2）**：
- **G1a 商品身份锁定**：为 HelloKitty 加长版与何佳功曲奇熊（135×105×135）找到独立商品页、商家、SKU、到手价、按 SKU 核实杆径；
- **G1b 缺失尺寸补齐**：详情图/说明书/评价图优先，必要时允许向卖家**仅索取尺寸照片**（仍禁止下单付款）；拿不到的字段走 **G1b 参数不确定性模拟**兜底（已完成：假设网格上"确定通过 / 存在条件 / 无法判断"三类判定与失效边界，见 `source-data/christmas-magic-tent/g1b/`）。
- **预算约束修正**：帐篷优先 ≤¥200（总预算 ¥500 中原预留额）；超 ¥200 的候选须重算完整 BOM ≤¥500 才能进入采购评审。
- 明确不走"买一实测"路线：7 天无理由要求商品完好、超查验范围可能影响退货，且"缺几个尺寸"不足以 justify 购买一整套帐篷。

## G2-V1 电子数字模拟完成（2026-11-07，零采购）

控制器逻辑 `controller.h` **原样复用**（md5 校验一致）通过主机逻辑测试 **8 类行为 / 11 场景全 PASS**（上电关闭、短按循环、长按关闭、去抖 29/30ms 边界、上电按住抑制、10 分钟超时 599999/600000 边界、快速连续按压、millis 回绕），原版 7 场景回归亦 PASS。Wokwi 项目（UNO R3 + 按钮 D2 + 4×WS2812 D6）编译通过、仿真运行、串口输出正确；**按钮交互截图待人工 5 分钟执行**（自动化未穿透 canvas），真实硬件验证阻塞于 Arduino 型号确认。详见 **[G2-V1 评审](/projects/christmas-magic-tent/g2-v1/)**。

## G2-V2 与 G1a 预算收敛（2026-11-07，零采购）

- **G2-V2 纯数字模拟完成**：新增 `greeter.h`（PIR 触发/冷却 15s/防重复/事件 Welcome↔Story 交替/按钮优先/上电预热抑制），**G2-V1 controller.h 零改动**；主机测试 6 场景全 PASS（连续触发、播放中再触发、手动按钮优先级、上电默认全覆盖），G2-V1 回归 11 场景 PASS。声音=串口事件模拟（PLAY_WELCOME/PLAY_STORY），未宣称 DFPlayer 验证。详见 **[G2-V2 报告](/projects/christmas-magic-tent/g2-v2/)**。
- **G1a 预算收敛**：~~主候选曾锁定 HelloKitty 160×100×130~~ **2026-11-09 采购决策更新：最终帐篷改为天猫哎哟宝贝 165cm 实木款 ¥210（CONDITIONAL BUY）**，HelloKitty 内容保留为历史比价（详见 [G1a 预算页](/projects/christmas-magic-tent/g1a-budget/) 与 g1a-final-report.md）。一次性合并采购清单（帐篷+装饰+电子四层，READY_BUY/BOARD_DEPENDENT/SIZE_DEPENDENT 分级）见 **[采购合并清单](/projects/christmas-magic-tent/consolidated-purchase-plan/)**。

## 帐篷采购放行（2026-11-07，用户拍板）

> **【已作废·仅作历史记录】** 2026-11-09 曾决策：确定购买 HelloKitty 单帐篷款 160×100×130cm ¥299.52（京东 10234458195367，下单由用户执行）；同日晚被天猫 165cm 实木杆款 ¥210 方案取代，**本段全部内容不再有效**。原风险兜底（7 天无理由+免费上门退换，门净尺寸/檐口高/杆径疑点转为到货实测项，9 项清单见 [G1a 预算页](/projects/christmas-magic-tent/g1a-budget/)）与原预算口径（帐篷 299.52 + 固定 260 = 559.52）随之失效；现行口径见页首与[采购合并清单](/projects/christmas-magic-tent/consolidated-purchase-plan/)。
