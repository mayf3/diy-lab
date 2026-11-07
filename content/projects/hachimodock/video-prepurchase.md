# HachimoDock｜Remotion 视频：买材料前先排除三个兼容风险

> **2026-11-07，制作状态：工程示意视频，不是硬件实测。** 本页使用原创 Remotion SVG 关系图与既有上游来源表，未使用官方 STEP、PCB 原图、装配录像，也没有真实开箱、焊接、亮屏。HachimoDock 项目目前仍处于准备阶段。

## 目标

用一条可复用的视频解释**为什么不能只按“ESP32-P4 + 2.8 英寸屏 + 3D 打印”直接下单**，以及 AI Agent 怎样代替零基础制作者先做版本和兼容调查。

[打开 HachimoDock 采购执行单](/projects/hachimodock/purchase-plan/) · [Agent 执行版](/projects/hachimodock/agent-track/) · [Remotion 模板与制作说明](/guide/remotion/)

## 视频中讲清楚的事情

1. **主控芯片**：微雪开发板的 `-M` 后缀不能说明 silicon v1 或 v3；必须配对实际芯片版次和对应固件。
2. **屏幕排线**：2.8 英寸、480×640 只是部分规格；还要确认 MIPI-DSI 驱动、屏幕模组、22P FFC 的触点方向和长度。
3. **PCB 和按键**：PCB 工程 BOM/原理图有明确型号 `CPG135001D01/C400229 ×3`，但按键/键帽高度和外壳配合仍需要结构证据；PCB 网表版本也尚需确认。
4. **打印方式**：即使读者没有 Bambu P1S，也可以通过自有机器、借用设备或代打印服务获得外壳。
5. **付款前的停止条件**：没有精确商品链接、兼容证据和含运费实际报价，就保留 HOLD；Agent 负责专业查证，真人保留付款决策。

## 观看

**Remotion 视频已生成并发布。** [直接播放 MP4](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-hachimo-20261107/hachimo-prepurchase-remotion-v1.mp4) · [下载 SRT 字幕](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-hachimo-20261107/hachimo-prepurchase-remotion-v1.srt) · [在 Maker Lab 视频工坊播放](/videos/)。目前为无配音的字幕动画，仍需后续真人素材补全真实硬件教程。

## 怎样看懂视频里的图？

所有主控、排线、PCB、机壳以及采购流程都是**便于学习的抽象 SVG 图形**，用于帮助新手理解关系；不是精确 CAD 外形，也不可以作为接线、焊接或 PCB 打样的制造依据。确切引脚、型号、尺寸请查 [官方硬件项目](https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc) 和由 Agent 阅读后的 [采购执行单](/projects/hachimodock/purchase-plan/)。

## 验收

- [ ] 观看者能说出三类会导致买错东西的兼容问题。
- [ ] 能根据自身条件选择打印 / 借用 / 代打印路线。
- [ ] 能区分“上游资料检查过”与“实际实物验证成功”。
- [ ] 能把技术调查交给 Agent，并保留最后购买授权。

## 出问题怎么办

若视频中版本与执行当天的 [官方 Release](https://github.com/YizhengWw/HachimoDock/releases/latest) 不同，先让 Agent 重新核验上游；**视频不会成为固件版本、商品实时价格或硬件兼容结论的唯一依据**。如果实际商品与示意图不同，以原厂规格与实物测量为准。
