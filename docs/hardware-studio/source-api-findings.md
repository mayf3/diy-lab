# 嘉立创 EDA Source API 自动化发现（2026-11-28）

**纠错：此前「EDA 无程序化元件放置能力」的结论不完整。** 编辑器内嵌 Source API
（`sch_SourcePrimitiveComponent/Wire/Pin/Attribute` + `lib_Device.search`）完整支持
放置/改号/导线/网络标签/引脚几何读取，全程无需鼠标与可见 GUI（headless 会话即可）。

## 验证过的调用契约（V4.1.105，2026-11-28 增补）

| API | 契约 | 备注 |
| --- | --- | --- |
| `lib_Device.search(key)` | 单参数返回数组 | 结果限 LCSC 系统器件库；不支持库范围参数 |
| `sch_SourcePrimitiveComponent.add` | projectId+schematicName+pageName+libraryUuid+name+x/y；**可选 designator 直接指定位号** | libraryUuid 用工程 uuid `4ab9e526…` 可解析工程库；字符串 `"project"` 报 path 错误 |
| `sch_SourcePrimitiveComponent.update` | **`designator` 字段改位号（本轮实测生效：U1–U4→K1–K4、H1/H2→J1/J3，get 读回一致）**；`properties` 改业务属性（按键增量覆盖） | **此前改号失败根因：误用 updateAttribute——其选项注释即「属性显示与位置修改」，不改值** |
| `sch_SourcePrimitiveComponent.updateAttribute` | 仅属性显示/位置 | 不能改 Designator 值 |
| `sch_SourcePrimitiveComponent.replace` | primitiveId+libraryUuid+name | 替换器件绑定 |
| `sch_SourcePrimitiveComponent.addNetFlag` | type=`Ground`/`Power`（ESCH 枚举无 NC 类型）+net+x/y | 地符号 rotation=0 引脚在上 |
| `sch_SourcePrimitiveWire.add` | line: `[[x,y],...]`；**共享端点的连续导线会自动合并为同一 primitiveId（折线）** | 电气连通性不变 |
| `sch_SourcePrimitiveAttribute.addNetLabel` | x+net；**标签必须精确落在导线端点** | 按名称并网 |
| `sch_SourcePin.getGeometry` | 返回 `{ok,value:[{pinId,pinNumber,x,y,side,length,bodyBBox}]}` | pinId=primitiveId+`-e*` 元素 id；ERC primitives 需经此映射回引脚号 |
| `sch_Drc.check(true,false,true)` | 返回数组 `[{type:'warn',rule:'CHECKFLOATPIN',primitives:[...]}]` | 接线后 SHOWDANDLING 归零 |
| `sch_Netlist.getNetlist()` | 返回 **JSON 字符串**（components 表含全部 props；无 nets 键） | 结构化器件表 |
| `sch_ManufactureData.getNetlistFile(name,'Protel2')` | 返回 File，`.text()` 读 PROTEL 网表 | **需图页文档已加载**（openDocument 后） |
| `sch_Document.save()` | 已无未保存变更时返回 false（异步落盘已生效） | 非错误 |
| `dmt_EditorControl.openDocument(uuid)` | **位置参数**（uuid 字符串）；对象参数静默无效 | 重开会话必须先 openDocument 才能导网表/读画布 |
| 源数据类（`sch_SourcePrimitive*`/`sch_SourcePin`） | "强制异步落盘"：写后紧读可能拿到旧值；**不依赖图页画布**，重开会话即可读 | 导网表例外（需画布） |

## 边界（本轮实测确认，headless 不可行）

- **器件库结构写操作不可用**：`lib_Device.create`（位置参数可创建但符号绑定无效，放置报"符号没有可用 PART"）；`lib_Symbol.updateDocumentSource` 一律返回 false（三种参数序均试）；`lib_Device.delete`/`lib_Symbol.delete` 报空错误。个人库残留测试记录：设备 5 条（5bf8be19…、bc5ca4ea…、fd4d4b13…、b328301d…、1679d683…）+ 空符号 1 条（afca6ddb…），可在 GUI 库管理器手动删除，不影响 R1 工程。
- **Footprint/Symbol/Device/FootprintName 为结构属性**：`properties` 修改被 API 明确拒绝（"属性 Footprint 不允许通过 properties 修改"）；空字符串覆盖被忽略，非空值生效。因此开关的 FOOTPRINT 占位（SW-SMD_C9900017374）保留为**隔离占位**并机器登记（eda-assert-netlist.py QUARANTINED 条目）， Supplier Part/3D Model Title/JLCPCB Part Class/Manufacturer Part/LCSC Part Name 已全部改为通用声明 + TBD-MECH-AXIS。
- **`replace` 强制引脚号集合一致**（3 脚器件不能 replace 成 2 脚器件，报"引脚号集合不一致"）；换电气脚数 = `remove` 旧件 + `add` 新件（add 支持 `designator` 直接指定位号）+ 按新引脚几何重接线。
- **`Add into BOM` / `Convert to PCB` 可经 `properties` 修改**（"yes"→"no" 生效并进入网表导出；`Add into BOM=no` 使 BOM 真实导出排除该器件——`sch_ManufactureData.getBomFile(name,'csv')` 验证零行）。结合换两脚符号，SMD 占位封装被语义隔离：无法进入 PCB，无法进入 BOM。
- **本地临时工程残留**：隔离实验工程 `SB-R1-Lab-Isolation`（uuid da7e9ed9…，位于 `~/Documents/LCEDA-Pro/projects/`）验证完成后 `deleteProject` 返回 false（headless 删除不可用），可在编辑器工程列表手动删除；不影响 R1 工程。
- `sch_Document.getElementsInRegion(region)` 枚举图页元素（primitiveId/type/net/坐标），是批量清理与核对的可靠入口；本轮据此发现并清除了上一轮遗留的 16 个偏移网络标签重复件。
- 工程本地双通道同步：`.eprj3` 文件夹工程（`~/Documents/LCEDA-Pro/projects/Space Buddy Deck R1/`），`.esch2` 为行式 `head||payload|` 格式；重开本地工程会生成新实例 uuid（4a7cbe80…），Schematic/P1 uuid 不变。

## 正式工程状态（Space Buddy Deck R1，uuid 4ab9e526…，2026-11-28 隔离轮）

- 元件与位号：J1/J3（BX-PM2.54-1-22PY，C18078140）+ K1–K4（两电气脚通用开关，YD-3410 承载，
  Supplier Part=TBD-MECH-AXIS，Add into BOM=no，Convert to PCB=no）
- 占位隔离：C9900017374 整份网表零出现；BOM 真实导出仅 J1,J3 一行；占位封装
  SW-SMD_L3.9-W2.9-LS4.8-EH-A 被 Convert to PCB=no 语义隔离（非文字声明，机器断言强制）
- 开关引脚语义：仅 pin1/pin2 两电气脚（MX 轴塑料定位脚不入网表）；开关浮动脚 ERC 警告消失
- 网表（真实导出+52 项机器断言全过）：GPIO4={J1-4,K1-1} GPIO5={J1-5,K2-1}
  GPIO6={J1-6,K3-1} GPIO7={J1-7,K4-1} GND={K1-2..K4-2,J1-22,J3-1,J3-21,J3-22}
- ERC：0 error / 2 组 CHECKFLOATPIN（36 引脚全部=排母预期未使用引脚）；SHOWDANDLING=0
- 持久化：换件+隔离→异步落盘→会话关闭→工程重开→导出→再导出逐字节一致（d3f46041…）
- 断言脚本：`hardware/space-buddy-r1/eda-assert-netlist.py`（--check 只断言；参数化
  --net/--json；check_project.py 已接入——哈希同步篡改仍会被语义断言拒绝）
