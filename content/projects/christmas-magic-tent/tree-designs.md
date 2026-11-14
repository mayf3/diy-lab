# 圣诞树双方案对比｜平面骨架树 vs 立体骨架树

> **证据分级**：本页全部为**数字建模与渲染**（已建模、已渲染）——**未切片、未打印、未试装**。帐篷为占位尺寸（165×105×135cm，商家规格，未实测）；模型尺寸正确不等于接头牢固或整树稳定。

## 两方案整体对比

**左：方案 A 平面开放骨架树（推荐）｜右：方案 B 立体骨架树**

![两方案裸骨架与帐篷占位的比例对比](/media/christmas-magic-tent/tree-v2/compare_side_by_side.jpg)

同一 Blender 参数化模型（`tree_designs_blender.py`）产出全部视图与打印文件——图中的底座、接头、横梁在 STL 里一一对应。

## 方案 A（推荐）｜平面开放骨架树

![方案 A 装饰后效果图：绿色装饰板、白雪带、树顶星、红礼盒（布艺/3D 件示意）](/media/christmas-magic-tent/tree-v2/tree_decorated.jpg)

- 结构：中央 30×30 方管立柱 ×3 段堆叠，5 层双侧横梁形成三角轮廓，A 字双脚 + 横撑。
- 推荐理由：
  1. **打印件 25 个、16 颗 M4 顶丝**——比方案 B（48 件/30 颗）少近一半，拼装与收纳成本最低；
  2. 两面横梁的中央夹层天然**夹持 2D A4 拼接图案板**——2D 图案与 3D 装饰件同屏成立，正好实现「2D 打印 + P1S 装饰 + 灯光」的分工；
  3. 横梁全可拆平放，收纳最薄；A 字脚独立站立，不依赖帐篷杆/门帘承重；
  4. 零件最大外形 245mm，全部在 P1S 256mm 床内，平放打印、基本免支撑。

## 装配方式（爆炸图 + 动画）

![方案 A 爆炸图：立柱段上浮、节点分层、横梁向外、脚架在底部](/media/christmas-magic-tent/tree-v2/tree_exploded.jpg)

- **装配顺序**：A 字脚 + 横撑 → 立柱 3 段（套筒接头）→ 5 个横梁节点（M4 顶丝 ×2/个）→ 插横梁 → 夹 2D 图案板 → 挂 3D 件 → 树顶星。
- **装配动画**（爆炸→装配，108 帧）已生成于 `source-data/christmas-magic-tent/tree-v2/renders_local/anim_frames/`，合成命令见同目录 note 文件；MP4 不入 git。

## 方案 B｜立体骨架树（可选第二件）

![方案 B 比例图：帐篷占位（165×105×135cm 待实测）与两棵树](/media/christmas-magic-tent/tree-v2/tree_scale.jpg)

四面可看、立体感强，但打印件翻倍（48 件）、紧固件翻倍（30 颗）、收纳体积大。**建议作为独立摆件第二期再说**，不与 V1 抢工期。

## 统计与预算口径

| 项 | A（推荐） | B |
| --- | --- | --- |
| 打印件总数 | **25** | 48 |
| 零件种类 | 19 | 16 |
| 紧固件 | **16**（M4 顶丝+蝶母） | 30 |
| 新增材料（非打印） | M4 顶丝蝶母 16 套；5mm 瓦楞板 1–2 张；A 字支架材料 | 同左 + 更多圈段耗材 |
| 预计 PETG | 主体+装饰 ≈120–200g | 更多 |

完整 V1 采购口径见 [V1 统一 BOM](https://github.com/mayf3/diy-lab/blob/main/source-data/christmas-magic-tent/v1/v1_wled_bom.csv)；灯串/控制器两件 SKU 待卖家确认线序后才能付款。

## 文件入口（全部已生成，几何级）

| 文件 | 路径（仓库内 `source-data/christmas-magic-tent/tree-v2/`） |
| --- | --- |
| 可编辑工程 | `generated/blends/tree_designs.blend` |
| 单件 STL | `generated/stl/A/*.stl`（19 类）、`generated/stl/B/*.stl` |
| 首盘试件 3MF | `generated/3mf/first_plate.3mf`（4 件，几何+摆盘，**不含切片配置**） |
| A4 纸样模板 | `../v1/generated/a4/`（12 页 SVG，100% 打印 + 十字校准线） |
| 生成脚本 | `tree_designs_blender.py`、`make_decorations.py`、`make_a4_tree.py`、`make_3mf.py` |
| 几何检查 | `generated/assembly_check.json` + `generated/stats.json` |

## 首盘试件（先打这一盘）

| 零件 | 目的 | 观察点 |
| --- | --- | --- |
| `A_joint_L1.stl` | 关键接头：横梁双层插座 | 插入横梁后是否晃动；顶丝孔是否通 |
| `A_col_sleeve1.stl` | 立柱对接套 | 与 30×30 梁端配合松紧（目标：手劲可拆、不自行滑落） |
| `A_beam_L5_L.stl` | 最短横梁 = 骨架小样 | 平放打印的表面与端头质量 |
| `A_star.stl` | 可复用星星（亦用于帐篷顶） | 内凹角是否需要支撑；尖角强度 |

打印设置建议：PETG、0.2mm 层高、平放、支撑仅树顶星内凹处。打印后核对：卡扣内宽与背板厚度、横梁插入手感、星尖无裂纹。**试装不合格 → 改公差重印，不要硬装**。

## 状态账本

已建模 ✅ · 已渲染 ✅ · 已切片 ❌ · 已打印 ❌ · 已试装 ❌ · 帐篷实测 ❌（未下单）
