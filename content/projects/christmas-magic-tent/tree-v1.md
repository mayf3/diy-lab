# 圣诞树 V1｜3D 打印骨架，灯光由软件决定

> **数字设计已生成；没有购买 WLED 控制器或灯串，也没有实物验收。** 2026-11-11。本路线专注一棵独立的可编程桌面圣诞树，仍然不让电子模块承重或固定在帐篷上。

![数字 CAD 示意：交叉式可拆树体，未加灯串，非真实打印或成品](/media/christmas-magic-tent/tree/tree-v1-preview.webp)

## 目标

让 Bambu P1S 负责树体，让成品 5V 可逐颗控制的 RGB 灯串负责光，让预装 WLED 的封装控制器运行动画。基本不焊电路，后来想增加复杂效果、Agent Button Deck 四键切换、时间表或音乐同步时，主要改 **软件场景** 即可。

## 准备什么

- 树体：打印两块交叉树板加一个底座，源文件、STL、STEP 都在 [tree-v1 原始设计目录](https://github.com/mayf3/diy-lab/tree/feat/christmas-tree-wled-software-first/source-data/christmas-magic-tent/tree-v1)。
- 灯：**5V WS2812B/SK6812 逐颗寻址成品灯串，约 20 颗，已焊、3Pin 插头**。不要买普通 USB 彩灯串，它的灯珠未必能被软件逐颗控制。
- 控制器：**预装 WLED 的 5V USB 封装控制器**，以 [GLEDOPTO GL-MC-001WL 官方型号](https://gledopto.com/h-pd-110.html) 为基准。不要误买 12–24V 版本。
- 电源：合格 5V USB 成品适配器，确认双口输出总量；只使用可靠且极性匹配的预制灯串接口。首次测试须检查供电电流与温升。

**本路线两件新增灯光商品的商家 SKU、运费和购物车尚未确认**。精确采购要求见 [tree-v1 采购门禁](https://github.com/mayf3/diy-lab/blob/feat/christmas-tree-wled-software-first/source-data/christmas-magic-tent/tree-v1/purchase-spec.md)，不能把此前约 ¥423.53 的帐篷购物车当作已包含它们。

## 第一步：用 P1S 打印一棵小树

下载并用 Bambu Studio 打开三份 STL，打印时**平放在打印床上**，先看切片预览有没有薄壁和悬空。默认高约 23.5cm、最宽约 19.2cm、底座约 17.5cm，三片均在 P1S 的 256mm 打印平台尺寸内。建议 PETG，0.2mm 层高；打印前确认卷料及切片估算，不把 CAD 验证冒充真实可用的卡扣。

下载：
- [顶部开槽树板 STL](https://github.com/mayf3/diy-lab/raw/refs/heads/feat/christmas-tree-wled-software-first/source-data/christmas-magic-tent/tree-v1/generated/tree_panel_top_slot.stl)
- [底部开槽树板 STL](https://github.com/mayf3/diy-lab/raw/refs/heads/feat/christmas-tree-wled-software-first/source-data/christmas-magic-tent/tree-v1/generated/tree_panel_bottom_slot.stl)
- [十字底座 STL](https://github.com/mayf3/diy-lab/raw/refs/heads/feat/christmas-tree-wled-software-first/source-data/christmas-magic-tent/tree-v1/generated/tree_cross_base.stl)

两个树板从相反方向插到中心，再把底边卡进带凹槽的底座。默认孔槽净间隙 0.5mm，**实际装配先试，不顺畅就修改并打印小样，不要硬敲**。用现有可拆的软理线带从树板预留孔绑住灯线，保留随时拆灯的可能。打印件边角需要检查，小件不适合儿童单独玩。

## 第二步：插成品灯串，不自己做焊接电路

核对控制器输出和灯串输入上的 +5V / GND / DIN 以及接头公母。**同为 3Pin 不代表线序一定一样**；证据不足就暂停购买，实际线序与极性不符也不插接。所有电子件、适配器、线缆独立放在帐外、儿童够不到的位置，不靠帐篷杆承重。

## 第三步：用 WLED 软件点亮并扩展

控制器入网后，在 WLED LED Preferences 中选择 WS281x/正确灯珠数量，测试 GRB 颜色顺序，并将最大 LED 电流限制暂设为 700mA。20颗 WS2812B 在满白全亮可能接近 1.2A，控制器也用电，不能只看USB接口就认为无安全风险。先用低亮度暖色测试，不直接拉满白。

电脑端不用安装专门开发框架，Python 标准库就可以发送 WLED JSON API。

先演示（默认 dry-run，不会连接灯）：

    python3 source-data/christmas-magic-tent/tree-v1/tree_wled.py --host 192.168.1.88 warm

确认真实 WLED 局域网地址、灯串与电源已通过实物检查后，再实际发送：

    python3 source-data/christmas-magic-tent/tree-v1/tree_wled.py --host 192.168.1.88 --live sparkle
    python3 source-data/christmas-magic-tent/tree-v1/tree_wled.py --host 192.168.1.88 --live night
    python3 source-data/christmas-magic-tent/tree-v1/tree_wled.py --host 192.168.1.88 --live off

颜色、亮度、速度和效果名称只需修改同目录 scenes.json。程序**按设备实际效果列表动态匹配**，不硬编码效果编号；默认场景最高亮度 88/255。WLED 内置预设和动画在 Mac 断线后也能继续运行。参见 [WLED JSON API 官方说明](https://kno.wled.ge/interfaces/json-api/)。

### 以后接 Button Deck，不再布额外灯线

| Button Deck 事件 | WLED 场景 |
|---|---|
| K1 | warm 暖光 |
| K2 | sparkle 星光 |
| K3 | rainbow 彩虹 |
| K4 | off 关灯 |

Mac 端收到按键事件后可以通过已有授权动作路由调用这个脚本，不需要再让 Button Deck 直接焊接到圣诞树上。后续也可以用同样的 API 支持日程、欢迎语事件或者 Agent 控灯；当前**并未连接真实 Button Deck 或真实灯**。

## 验收

- [ ] STL/STEP 和源文件对应，P1S 切片无越界、无薄壁失败
- [ ] 两片树板和底座实际装配稳固，孔边没有毛刺或松脱
- [ ] 购买的是 5V 独立寻址灯珠，不是 12V 灯或普通不可寻址 USB 灯
- [ ] JST-SM 接头方向与实际 +5V / GND / DIN 线序逐针确认匹配
- [ ] WLED 实际 LED 数量、颜色顺序和电流限制已设好；测试无过热或自动重启
- [ ] 可以独立切换暖光/星光/彩虹/关闭，控制器和线材不在儿童可触及处

## 出问题怎么办

不通电：先确认是不是 5V 灯、灯的 DIN 是否朝向控制器、两端 3Pin 接头是否同序，再用低亮度尝试。出现异味、发热或重启，应立刻断电。Wi-Fi 连不上先检查 WLED AP 配网和 2.4GHz 网络，禁止将无认证的 WLED 局域网接口直接暴露互联网。若卡槽不适配，先小样重新调整，别用胶封死不可逆的组合。

**最重要的边界**：圣诞树是可编程独立装饰，与原帐篷的 UNO/PIR/DFPlayer 属于不同分期路线。以“树先亮起来”为优先目标时，暂缓额外音频、PIR 和裸灯珠焊接，无需为此买整套焊台。
