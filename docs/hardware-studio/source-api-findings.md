# 嘉立创 EDA Source API 自动化发现（2026-11-28）

**纠错：此前「EDA 无程序化元件放置能力」的结论不完整。** 编辑器内嵌 Source API
（`sch_SourcePrimitiveComponent/Wire/Pin/Attribute` + `lib_Device.search`）完整支持
放置/改号/导线/网络标签/引脚几何读取，全程无需鼠标与可见 GUI（headless 会话即可）。

## 验证过的调用契约（V4.1.105）

| API | 必填字段 | 备注 |
| --- | --- | --- |
| `lib_Device.search(key, ..., itemsOfPage, page)` | 位置参数 | 返回 name/uuid/symbolUuid/libraryUuid |
| `sch_SourcePrimitiveComponent.add` | projectId + schematicName + pageName + name(器件库名) + libraryUuid + x/y | 返回 primitiveId + 自动位号；位号用 updateAttribute(key="Designator") 改 |
| `sch_SourcePrimitiveComponent.updateAttribute` | key+value（大小写敏感：`Designator` 存在但改后 get 读回未生效——位号改写待续） | |
| `sch_SourcePin.getGeometry` | primitiveId | 返回每针 x/y/side/length + bodyBBox |
| `sch_SourcePrimitiveWire.add` | line: `[[x,y],...]` 数组格式（对象格式报"坐标必须是有限数字"） | |
| `sch_SourcePrimitiveAttribute.addNetLabel` | x + net | **标签必须精确落在导线端点上**才并入网络（偏移 4px 都不连通） |
| `sch_Drc.check(true,false,true)` | — | 返回 [{type,rule,primitives}]；本轮 0 error / 10 warn（SHOWDANDLING×8 + CHECKFLOATPIN×2） |
| `sch_ManufactureData.getNetlistFile(name,'Protel2')` | 返回 File | `.text()` 可读 PROTEL 网表 |

## 正式工程状态（SpaceBuddy-R1，uuid 4ab9e526…）

- 已放置：J1/J3（KH-2.54PH90-1X22P-L13.8 排母）+ K1–K4（轻触开关 2 脚）+ 8 导线 + 8 网络标签
- primitiveId：J1=9219a882acbb9928 / J3=dd09a31e60381e2c / K1=15eb568866d1c5e4 /
  K2=d2021d0f73c9658a / K3=ce954863ed464ffb / K4=82f2e5a85940f6bb
- 网表（真实导出）：GPIO4=U1-1、GPIO5=U2-1、GPIO6=U3-1、GPIO7=U4-1、GND={U1-2,U2-2,U3-2,U4-2}
  ——**电气连接全部正确**（U1–U4 即 K1–K4，位号改写 API 生效问题待续）
- ERC：0 error / 10 warning（悬空网络警告=排母未接线，浮动引脚警告=开关第 3 脚未用，均为预期）

## 遗留（下一步）

1. 位号改写 API（updateAttribute key="Designator" 返回 ok 但读回未变；"Name" 键也试过）——待查官方文档属性名或用 update() 整体更新。
2. J1/J3 排母针未接（22×2 针与 GPIO 的物理对应在 G4 布局阶段做；ERC 悬空警告源于此）。
3. 原理图改名 Carrier（modifySchematicName 返回 false，前置条件待查）。
4. 开关第 3 脚（NC）处理：当前浮动，用 No-Connect 标记待 API 探查。
