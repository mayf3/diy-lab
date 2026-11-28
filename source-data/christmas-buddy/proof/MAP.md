# MAP：Release 模型 ↔ Manifest Checker ↔ 制造工件 ↔ 测试

本文档是 M5 发布合同的**实现映射**（governance 三层证据的第二层）。
原则：Lean 证抽象合同；Python Checker 证真实文件绑定；两者经 `ReleaseCurrent.lean`
受控转换连接——任何一侧私自改语义都会被 `m5_manifest check` 抓住。

## 数据流（单向，任何输入变化触发重新验证）

```
真实文件 ──sha256──▶ m5_manifest.json（release 候选）
                        │ gen_lean()（受控转换，禁止手写哈希）
                        ▼
              ReleaseCurrent.lean（AUTO-GENERATED）
                        │ lake build（编译即验证 currentTuple 不可制造）
                        ▼
              verification.json（公理审计回执）
                        │ （verification.json 本身是受管工件 → 回写 manifest）
                        ▼
              m5_manifest check（漂移 = FAIL = 新候选，旧批准不继承）
```

收敛性：manifest_hash 依赖 verification.json，verification.json 由含 manifest_hash 的
ReleaseCurrent.lean 编译产生 → 需两轮 build/verify 收敛到不动点（已实测 2 轮收敛）。

## 追溯矩阵

| ID | 模型/定理（Lean） | 实现映射（Python/文件） | 测试（正向/负向） | 证据状态 |
|---|---|---|---|---|
| MOD-M5 | Version.lean：Release/complete/isFrozen/manufacturable | m5_manifest.py v2 ARTIFACT_TABLE | m5 check 正常路径 | PROVEN + TESTED |
| THM-完整性 | thm_frozen_are_complete / thm_complete_sound | gen_lean: complete 字段由 tuple 生成 | 生成文件编译即验证 | PROVEN |
| THM-不可造 | thm_incomplete_never_manufacturable / thm_unapproved_not_manufacturable | check(): approval_state=UNAPPROVED + tuple none | ReleaseCurrent.lean 的 `example ... = false := by rfl`（对真实候选数据验证） | PROVEN（模型）+ TESTED（数据） |
| THM-唯一性 | thm_release_ext（四段逐一相等 ⇔ 值相等） | 哈希集合生成 manifest_hash：任一工件变 → hash 变 | check() 漂移检测（已实测：Version.lean 改动后 check FAIL，重建出新候选） | PROVEN + TESTED |
| THM-不继承 | manufacturingRelease 三重门禁 + 注册表不含旧候选 → 不可制造 | approval_state 不随 build 继承，仅 GATE 人工写回 | check() 断言 approval=UNAPPROVED 时 Lean 常量必须为 false | PROVEN（模型）+ TESTED |
| THM-注册 | thm_registry_membership_implies_approved | approvedRegistry 为空（本轮无任何批准） | — | PROVEN |
| MAP-身份 | currentManifestHash = manifest.release_candidate.manifest_hash | check() 断言 Lean 文件内嵌哈希 == manifest | check() 失败路径已实测 | TESTED |
| OB-1 | （无——存在性不证明） | NOT_YET 工件 10 项：Gerber/PCB 源/固件/试打印报告等，**不携带虚构哈希** | check(): NOT_YET 出现文件即 FAIL 提示升级 | TESTED |

## 证据状态声明（不得互相冒充）

- **PROVEN**：Version.lean 26+ 定理（公理白名单内）——只约束模型，不约束真实文件。
- **TESTED**：manifest build/check、漂移拒收、NOT_YET 升级提示、Lean-MAP 一致性断言——
  真实文件层，由脚本与负向路径实测承担。
- **NOT_YET**：Gerber/PCB/固件/试打印尚不存在；`manufacturable = true` 在本阶段
  **对任何候选都不成立**（by rfl 对真实数据验证）。
- 本表禁止出现的声明：「Lean 编译通过 = 制造文件通过」（从未发生，也永不应发生）。

## 更新流程（谁改了什么怎么办）

1. 改任何工件 → `m5_manifest.py check` FAIL（漂移）。
2. 重跑 `m5_manifest.py build` → 新 manifest_hash → 生成新 ReleaseCurrent.lean。
3. `verify_proof.py` 重跑（编译生成文件 + 公理审计）→ verification.json 更新。
4. 再 `build` 一次使 manifest 收敛（verification.json 是受管工件）。
5. 若候选要进制造：**必须人工走 GATE 门禁**，approval_state 才能由 UNAPPROVED 变更，
   且四段 tuple 必须同时冻结为新整数版本。
