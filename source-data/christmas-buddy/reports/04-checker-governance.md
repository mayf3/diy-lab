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

## Batch4.2 发布合同收口（PR #36 两条 Review Finding + 批准注册表）

| 检查器 | 正向 | 负向 | 故障注入 | 证据 |
|---|---|---|---|---|
| canonical 规范化（唯一实现） | A14 嵌套符号链接 basename序≠完整路径序：build→check PASS 两轮、哈希稳定 | 修复前反例复现：同一树 build 后立即 canonical hash 不一致 FAIL（PR#36 Review #4727196824） | —（排序统一由 canonical_payload 单点实现） | 对抗矩阵 v3 A14 |
| 批准人身份精确匹配 | Lean thm_registered_exact_approval_manufacturable + reg_caseA | thm_approver_identity_mismatch / reg_caseB（GATE-test vs OTHER）/ reg_caseC（空串） | — | Version.lean + ReleaseCurrent.lean |
| 注册表成员资格 | reg_caseA（记录在表 → 可制造） | reg_case3 哈希不符 / reg_case4 release 不符 / reg_case5 未登记 / reg_case6 空注册表，全部不可制造 | — | ReleaseCurrent.lean（by decide） |
| 批准治理（Python 层） | 真实候选 UNAPPROVED+空注册表 → check PASS | A15 APPROVED 无精确记录 / A16 UNAPPROVED 带记录 → 精确诊断 | **A15-FI 禁用 approval_consistency 后诊断消失** | 对抗矩阵 v3 |
| gen_lean 真实数据映射 | A 真实 Manifest→不可制造断言编译通过；B 隔离 APPROVED Manifest→可制造断言编译通过 | C 批准人不同 / D 记录未登记 / E 四元组变更 → R1 断言 false≠true → **编译失败（Lean 拒绝矛盾数据）** | FI 禁用治理规则后 C/D/E 诊断消失 | manifest_lean_gen_tests 7 案 |

外部信任边界（明确声明）：Lean 证明的是「批准记录在受信任注册表中且字段精确一致」这一结构事实；
现实中批准人的身份与授权真实性由工作台 GATE 门禁与受控批准记录流程负责。任何文档不得宣称
Lean/脚本验证了「现实中的人」的身份。

生产注册表现状：`release_candidate.approval_records = []`（保持为空），真实候选 UNAPPROVED；
测试只使用隔离注册表（isolatedTestRegistry / 临时 Manifest），不写真实文件。

## Batch4.3 双层哈希解环与动态冻结（PR #37 Review #4727422072）

| 检查器 | 正向 | 负向 | 故障注入 | 证据 |
|---|---|---|---|---|
| release_hash（内容身份） | 定版 UNAPPROVED → 批准 → 重建：release_hash 逐位稳定 | N2 PCB/N3 BOM 漂移 → 实时重算不一致；N5 四元组变化 → 旧批准失效（含冻结缺失诊断） | —（实时扫描与 build 共用 scan_artifacts 唯一实现） | gen 测试「解环」案例 + N2/N3/N5 |
| manifest_hash（封套） | 批准元数据变化 → 封套变化而内容身份稳定 | N7 手改登记值 → 重算不一致 FAIL | — | gen 测试 N7 + 解环案例 |
| 合法批准全链 | **POS-B：spec → release_hash → 绑定记录 → 重建 → M5.check PASS → Lean 编译 PASS → 公理审计 PASS**（旧模型数学上不可完成，修复 #4727422072） | N1 旧 release_hash / N4 批准人 / N6 删记录 / N8 改状态各自精确 FAIL | FI 禁用 approval_consistency 后治理诊断消失 | manifest_lean_gen_tests 13 案 |
| 动态冻结注册表 | 混合版本 PCB=2/CAD=1/FW=3/BOM=2 合法冻结+批准 → Python check 与 Lean（thm_mixed_version_* / reg_mixed_exact_match）双 PASS | reg_mixed_not_frozen / reg_mixed_empty_frozen（Lean）；N5 冻结缺失诊断（Python） | — | Version.lean v6 + 生成文件 14 定理 |
| release-spec 受控输入 | build 从 spec 读取（不再硬编码空四元组）；spec↔manifest 一致性比对 | 缺失/结构非法 → build 异常拒绝；手改 manifest 伪造冻结 → spec 不一致 FAIL | — | load_release_spec + check |

生产现状：release-spec.json（UNAPPROVED / 空冻结注册表 / 空批准注册表）；双层哈希规范全文见
`reports/06-two-layer-release-hash.md`。本批后制造验证框架冻结，转入真实 EDA 工程与 PCB Layout。
