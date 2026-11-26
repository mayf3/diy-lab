# EDA 与硬件产品化

## 目标

把合适的 Lab 项目做成最终可使用的硬件产品：由工厂完成约定范围的焊接，配合 3D 打印外壳，让用户主要负责插接、固定和使用。每个项目都比较现成模块、预焊模块加载板、全定制 PCBA 三条路线；不要求用户先学习手工接线，也不要求所有项目都做 PCB。

## 本次真实状态（2026-11-26）

- Mac 已安装 `/Applications/嘉立创EDA(专业版).app`。CLI 实测版本为 `4.1.105.0339a6cd`，签名核验有效；`Info.plist` 中的 `2.2.32.4` 是应用外壳版本，不作为编辑器版本。
- `pcb-product-delivery`（PCB 产品交付）与 `lceda-pro-automation` 已在云端和 Mac 安装。前者负责产品、制造和板壳交付，后者负责 EDA 操作。
- 已通过“文稿”访问权限步骤。`doctor` 返回 `connected=true`、版本匹配，客户端实际显示首次免费激活窗口。编辑器 `open` 受到激活步骤阻塞，尚无工程 API 往返成功证据；需在官方页面获取本人的免费激活文件并导入客户端。
- 原生 MCP 的握手、工具发现和 doctor 调用已经实测通过，并已登记到本地 Codex 的 lceda-pro 服务。实际工程读写仍需完成首次激活。详情见 docs/eda/environment-status.json。
- 本次尚未生成原理图、PCB 或可下单制造资料，没有采购或提交制造订单。HachimoDock 的既有 PCB 是历史设计，仍须复审。

本次记录位于独立工作区 `/Users/yanfenma/Documents/DIY/diy-lab-pcba`，分支 `codex/eda-pcba-setup-20261126`，基于 `origin/main@370786b`。不改动正在使用的其他工作区，也不更新站点数据。

## 项目路线

| 项目 | 当前建议 | 先完成什么 |
| --- | --- | --- |
| 四键 Button Deck | 首个小型 PCBA 候选：预焊开发板＋工厂装配载板＋打印外壳 | 核实准确开发板、按键、尺寸和全部焊点的装配范围 |
| HachimoDock | 复审既有 PCB 后再推进 | 解决 BK1 芯片、BK2 屏 FFC、BK3 PCB_V1.2 网表/几何、BK4 键轴封装四项 open 问题 |
| 随身记录器 | 保留 Pi 和摄像头模块，先结构集成 | 按最新选择核实模块与镜头；不重做高速主板 |
| KURA 圣诞布置 | 按最新“无屋顶”目标做结构和装饰 | 避免沿用 main 中过时的旧帐篷路线；不强加 PCB |
| SO101 | 保留现成控制板与线束 | 从实际装配问题判断是否需要局部转接板 |

可机读的完整项目记录见 `source-data/productization/projects.json`。Button Deck 候选说明见 `source-data/agent-button-deck/pcba-v1/product-brief.md`。

## Button Deck 的当前边界

已存在的方案位于 `origin/feat/agent-button-deck-doavr@5654c5d`，尚不在 main：ESP32-S3 DevKitC v1.1、GPIO4–7 四键、USB-UART 通信，已有源码但无实物验证。本轮先记录载板候选，不将该分支内容自动并入 main。

载板候选优先保持现有通信和固件接口。若将来改为全定制主板或原生 USB，必须连同固件和主机接口一起评估，不能默认兼容。

## 下一步产物

先使编辑器实际打开工程，再核实首个候选的准确部件与尺寸，形成连接表和可读原理图。随后才是 PCB、原生检查结果、工厂装配范围，以及与同版电路匹配的固件和外壳。

可供制造审查的一套资料通常包括原生工程、Gerber/钻孔、BOM、CPL 和检查结果；板子 STEP、外壳 STL/3MF、固件及装配验收记录共同支持整机交付。当前这些新资料均未形成，不以占位文件或伪造成功报告代替。

## 官方依据

- [嘉立创 EDA 下载](https://lceda.cn/page/download)
- [客户端运行模式、激活与本地工程](https://prodocs.lceda.cn/cn/faq/client/)
- [官方 CLI/MCP 指南](https://prodocs.lceda.cn/cn/api/guide/cli.html)
- [BOM、PCB 与 SMT 下单说明](https://prodocs.lceda.cn/cn/schematic/export-order-parts/)
- [坐标文件导出](https://prodocs.lceda.cn/cn/pcb/export-pick-and-place-file/)
- [PCB 的 STEP 导出与缺模型限制](https://prodocs.lceda.cn/cn/pcb/export-3d-file/)
- [外壳 STL/STEP 导出](https://prodocs.lceda.cn/cn/pcb/export-3d-shell-file/)

选料时重新核实工厂可贴装状态；商城有货不等于 SMT 有货，工厂焊好也不等于整机功能已通过。
