# CAD/网表检查器测试治理（Batch3 §四）

检查器本身是受验证的软件产品：其源码全部纳入 M5 manifest BOUND（netlist.py/netlist_tests.py/build_mech.py/openings.py/mech_tests.py/coupon_verify.py/coupon_tests.py/m5_manifest.py）。

## 规则登记（输入/输出/失败条件/负向案例）

| 检查 | 输入 | 失败条件 | 负向案例 |
|---|---|---|---|
| ERC 多驱动/悬空/电压域 | netlist nets | 任一规则触发 | netlist_tests T5/T6n 等 |
| ERC 上拉域（P0-1 类） | passive 两端电压域 | 5V→3V3 逻辑 IN | T1n |
| ERC 驱动隔离（P0-2 类） | 含晶体管下拉网 | 直连推挽 OUT | T2n |
| ERC 翻译器方向（P0-3 类） | translator attrs | DIR 网≠VCCA | T3n |
| ERC LED 链拓扑 | 4 级链 net | DIN 缺失/多源 | T4n |
| 装配布尔/弦长/总高 | 建模实体+参数 | 体积>阈值/弦长不足 | mech_tests 删孔/缩槽 |
| 几何开孔（STEP 重导入） | 导出 STEP 探针 | 探针干涉>1e-6 或面积不足 | mech_tests 三变体 |
| 测件 R1-R6 | 导出 STEP 探针 | 断裂/盲孔/超差/缺孔 | coupon_tests 六案 |
| M5 漂移/一致性/目录哈希 | 真实文件 sha | 漂移/损坏/顺序异常 | 对抗矩阵 A1-A12 |

## 铁律
1. 异常不得转换为 PASS（ coupon_verify 已改为异常上抛，Boolean 空结果才=通过）。
2. UNKNOWN 不自动升级（assembly_check.json unknowns 单列）。
3. 六层证据严格分级：参数 → CAD 构造 → STEP 几何 → STL → 切片 → 实物；当前 STL/切片/实物三层为 NOT_YET（试打印待人工执行）。
4. CAD 修改后 `python3 scripts/verify_all.py` 一键重跑全链（依赖序，含 STEP 重导入）。

## Batch4 检查器覆盖表（§四：正向/负向/故障注入）

| 检查器 | 正向 | 负向 | 故障注入 | 证据 |
|---|---|---|---|---|
| C1 几何（槽位/底板逐槽体积） | coupon_verify R1-R3 全 PASS | coupon_tests 出界/切穿/半切（审查反例 53.6 vs 期望 107.1 → FAIL） | partial-floor 变体 | 本轮输出 |
| C2 几何（贯穿/量规/连通） | R1/R4/R5 全 PASS | 盲孔/缩孔/删孔 FAIL | blind/shrunk/missing 变体 | 本轮输出 |
| C3 几何（封闭孔/包络/实体保留） | R1/R6/R7 全 PASS | 缩窄/顶部缺口/偏移 FAIL | top-notch/offset/shrunk 变体 | 本轮输出 |
| BOM 一致性 | 基线 PASS | A11 缺行诊断 | **A11-FI 禁用检查器后诊断消失（敏感度自检）** | 对抗矩阵 v2 |
| Gerber Manifest | A0 基线 PASS | A5-A8 内容/删/增/重命名各自精确诊断 | 目录规则从 check 中剔除的敏感度分析（A6 注释） | 对抗矩阵 v2 |
| Release 合同 | A0 + Lean 对真实候选 | A12 手工 APPROVED+漂移仍 FAIL | A13 Lean 数据核验 | 对抗矩阵 v2 |

原则执行：测试 PASS 必须意味着目标规则确实执行并拒绝了目标错误；每案独立干净基线+单一注入+精确诊断断言；禁用目标检查器后断言必须失效（A11-FI 模式，可复制到其他检查器）。
