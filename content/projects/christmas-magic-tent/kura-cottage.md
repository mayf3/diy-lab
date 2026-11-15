# 小屋设计基准 v2｜宜家 KURA 库拉床（502.665.06）

> **证据分级**：床型与尺寸 = 用户确认 + 宜家官方页（2026-11-15 查证）；斜屋顶 =
> 实拍疑似加装件（**非 KURA 标准结构**，几何全部待实测）；装饰效果 = 数字建模与
> 渲染（**未采购、未打印、未安装**）。

## 基准切换：帐篷 → KURA 床

「AI 圣诞魔法小屋」的设计基座由帐篷（165×105×135，占位）迁移为**宜家 KURA 库拉
两用床**：

| 口径 | 长 | 宽 | 高 | 备注 |
| --- | --- | --- | --- | --- |
| 设计基准（用户确认） | **209** | **99** | **116** | 床垫 90×200 |
| 宜家 HK 同款页（查证 2026-11-15） | 199 | 100 | 116 | 床底高 83；承重 100 kg；床垫最大 189×92×12 |

209 与 199 的口径差（包装尺寸 vs 本体尺寸）登记为 **TM-01**，卷尺实测后定稿。

## 组件区分（对照官方结构与实拍）

![KURA 结构区分标注：标准床架 / 床垫睡眠区 / 疑似加装斜屋顶](/media/christmas-magic-tent/kura-v1/kura_structure_labeled.png)

1. **KURA 标准床架**（承重构件）：4 立柱 + 顶平台框架（上沿 116 cm）+ 护栏带 +
   下铺洞屋侧板 + 板条底 + 平梯。**不改装、不开孔、不加载。**
2. **床垫睡眠区**：床垫 90×200 置于顶平台，**床垫顶面 = 睡眠区上界**。睡眠区内
   禁止绳环、垂布、悬挂硬件。
3. **疑似加装斜屋顶**（琥珀色标注）：实拍中的双坡结构不在 KURA 官方平顶矩形结构
   内，可能是额外配件。官方安装说明与更多实拍比对确认前，**不作为设计依据**，
   场景中独立组件参数化呈现。

## 两版装饰效果（可编辑场景已建：`source-data/christmas-magic-tent/kura-v1/`）

**① 极简原木森林圣诞屋**

![极简原木森林圣诞屋：原木/白双色剪影小树 + 雪花 + 山墙 PETG 星](/media/christmas-magic-tent/kura-v1/kura_deco_minimal.png)

原木/白双色剪影小树沿下铺洞屋外侧板排列（板缘夹固定），白雪花两枚，山墙端 PETG
星星。

**② 局部布艺魔法小屋**

![局部布艺魔法小屋：红白不织布门形框 + 白小树 + 雪花 + 护栏外侧星](/media/christmas-magic-tent/kura-v1/kura_deco_fabric.png)

红/白不织布门形框与白小树贴面（洞屋外侧板），雪花三枚，护栏外侧一颗 PETG 星
（床垫顶面以下，睡眠区外）。

## 装饰固定方式（合规红线逐条落实）

**不修改床架承重结构、不在床上安装额外挂钩、睡眠区不加绳环/垂布/悬挂硬件。**

| 方式 | 位置 | 合规性 | 待实测 |
| --- | --- | --- | --- |
| PETG 免工具板缘夹（C 形夹） | 下铺洞屋外侧板/端板顶沿（约 80 cm 高，睡眠区外） | 非挂钩、无螺丝、可拆卸、单件 ≤50 g | 板材厚度（TM-06）与夹持力 |
| 可移除魔术贴 | 侧板平面 | 可拆卸 | 贴面残留 |
| 配重立放 | 床旁地面（大剪影小树 + 底座） | 零固定 | — |

装饰物料：现有不织布（绿/白/红）+ 现有 PETG。**不采购新材料、不启动打印。**

## 待实测清单

| 编号 | 项 | 阻断什么 |
| --- | --- | --- |
| TM-01 | 长度口径 209 vs 199 | 场景基准 L 定稿 |
| TM-02 | 床垫实测 | 床垫参数 |
| TM-03 | 斜屋顶脊高（平台面→屋脊） | ROOF_RIDGE_H |
| TM-04 | 斜梁长度与根数 | 斜屋顶组件定形 |
| TM-05 | 斜梁/坡板连接位置 | 该组件保留与否 |
| TM-06 | 下铺板材厚度 | 夹具爪距选型 |
| TM-07 | 下铺净空与侧板高度 | 洞屋内部布置 |
| TM-08 | 顶护栏带截面 | 夹具与靠放验证 |

阻断器登记：`source-data/christmas-magic-tent/kura-blockers.csv`（K1–K5，open）。

## 工程文件

| 文件 | 说明 |
| --- | --- |
| `source-data/christmas-magic-tent/kura-v1/kura_cottage.py` | 参数化场景（Blender 5.2 headless，`--deco none/minimal/fabric/both`） |
| `source-data/christmas-magic-tent/kura-v1/generated/kura_cottage.blend` | 可编辑场景（组件分集合） |
| `source-data/christmas-magic-tent/kura-v1/renders_local/*.png` | 渲染原图（不入 git，已复制至 `public/media/christmas-magic-tent/kura-v1/`） |
| `source-data/christmas-magic-tent/kura-v1/README.md` | 设计基准明细 + 待实测清单 |
| `source-data/christmas-magic-tent/kura-blockers.csv` | K1–K5 阻断器 |

大型独立 3D 打印圣诞树（[tree-designs](/projects/christmas-magic-tent/tree-designs/)）**暂缓**，工程记录保留。
