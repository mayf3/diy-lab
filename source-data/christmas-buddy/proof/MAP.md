# MAP：Release 模型 ↔ Manifest Checker ↔ 制造工件 ↔ 测试

本文档是 M5 发布合同的**实现映射**（governance 三层证据的第二层）。
原则：Lean 证抽象合同与结构一致性；Python Checker 证 SHA256 与真实文件绑定；
工作台 GATE 负责现实授权——三层不得混淆。两侧经 `ReleaseCurrent.lean`
受控转换连接——任何一侧私自改语义都会被 `m5_manifest check` 抓住。

## 数据流（单向，任何输入变化触发重新验证）

```
release-spec.json（受控版本输入：tuple/frozen_registry/approval_state/approver/records）
        │
真实文件 ──scan_artifacts（build/check 共用）──▶ 双层哈希：
        │   release_hash  = SHA256(canonical(product, tuple, source_commit, artifacts, not_yet))
        │                   —— 产品内容身份（批准绑定层；不含任何批准元数据）
        │   manifest_hash = SHA256(canonical(release_hash, frozen_registry, approval_state,
        │                                   approver, approval_records))
        │                   —— 清单封套完整性（含 release_hash 值，不含自身：无自引用/无固定点）
        ▼
m5_manifest.json（release 候选，schema m5-release-manifest/3.0）
        │ gen_lean()（受控转换，禁止手写哈希；生成 currentReleaseHash/currentManifestHash/
        │            currentTuple/currentFrozenRegistry/currentRegistry）
        ▼
ReleaseCurrent.lean（AUTO-GENERATED；R1 把制造资格恒等于 approval_state，by decide 复核）
        │ lake build（编译即验证；矛盾数据 = 编译失败）
        ▼
verification.json（公理审计回执）
        │ （verification.json 本身是受管工件 → 回写工件扫描）
        ▼
m5_manifest check（8 步：工件 → release_hash 实时重算 → 批准精确匹配/成员资格 →
                   manifest_hash 重算 → spec 一致性 → Lean 绑定 → PASS/FAIL）
```

收敛性：verification.json 是受管工件 → 改动后需 build→verify→build→verify 两轮收敛
（verify_all 已实测两轮到不动点）。

## 追溯矩阵

| ID | 模型/定理（Lean） | 实现映射（Python/文件） | 测试（正向/负向） | 证据状态 |
|---|---|---|---|---|
| MOD-M5 | Version.lean：Release/complete/frozenWellFormed/manufacturableIn | m5_manifest.py v6 scan_artifacts + release-spec.json | m5 check 正常路径 | PROVEN + TESTED |
| HASH-双层 | （结构：ApprovalRecord.releaseHash 绑定 release_hash，与 manifest_hash 不得混用） | canonical_release_payload / canonical_manifest_payload（build/check 共用唯一实现） | 解环案例：批准元数据变 → release_hash 稳定 + manifest_hash 变 | TESTED（SHA256 层）+ OB-4/OB-5 义务登记 |
| THM-完整性 | thm_frozen_membership_complete（良构冻结注册表） | load_release_spec：frozen 条目必须完整四元组 | build 拒绝非完整冻结条目 | PROVEN + TESTED |
| THM-不可造 | thm_incomplete_never_manufacturable / thm_unapproved_not_manufacturable | check 批准治理 + R1（by decide 对真实数据） | A 真实候选 UNAPPROVED → R1 false | PROVEN + TESTED |
| THM-release_hash | thm_release_hash_mismatch_not_manufacturable | approval_consistency 精确匹配 releaseHash==release_hash | N1 绑旧 release_hash FAIL | PROVEN + TESTED |
| THM-冻结成员 | thm_unfrozen_not_manufacturable / reg_mixed_not_frozen / reg_mixed_empty_frozen | approval_consistency：APPROVED 候选须在 frozen_registry | N5 冻结缺失诊断 | PROVEN + TESTED |
| THM-混合版本 | thm_mixed_version_frozen_manufacturable / thm_mixed_version_manufacturing_release / reg_mixed_exact_match | POS-B 全链（PCB=2/CAD=1/FW=3/BOM=2 合法冻结+批准） | POS-B：check PASS + 编译 PASS + 公理审计 PASS | PROVEN + TESTED |
| THM-版本失效 | thm_version_change_invalidates_old_approval / reg_{pcb,cad,fw,bom}_bump_invalidates | 四元组变化 → release_hash 变 → 旧批准失效 | N5 + 生成文件 4 条 bump 定理 | PROVEN + TESTED |
| THM-注册 | thm_registry_membership_implies_approved / thm_unregistered_record_not_manufacturable / thm_empty_registry_not_manufacturable | approvedRegistry（生产空）/ currentRegistry（受控生成） | reg_mixed_unregistered / N6 / thm_empty_registry | PROVEN + TESTED |
| MAP-身份 | currentReleaseHash / currentManifestHash = manifest.release_candidate 对应字段 | check() 断言 Lean 文件内嵌双哈希 == 实时重算 | N7 伪造 manifest_hash FAIL | TESTED |
| SPEC-受控输入 | — | release-spec.json（不进 ARTIFACT_TABLE——批准元数据不得入内容基线） | build 缺失即异常；check spec↔manifest 比对 | TESTED |
| OB-1 | （无——存在性不证明） | NOT_YET 工件 10 项不携带虚构哈希 | NOT_YET 出现文件即 FAIL | TESTED |

## 证据状态声明（不得互相冒充）

- **PROVEN**：Version.lean 52 条定理（公理白名单内）——只约束模型与结构事实。
- **TESTED**：双层哈希计算、实时重算、漂移拒收、批准全链、spec 一致性——真实文件层，
  由脚本与正/负向路径实测承担。
- **NOT_YET**：Gerber/PCB/固件/试打印尚不存在；制造资格在本阶段**对任何真实候选都不成立**。
- 本表禁止出现的声明：「Lean 编译通过 = 制造文件通过」（从未发生，也永不应发生）；
  「Lean/脚本验证了现实中批准人的身份」（三层分工，GATE 负责）。

## 更新流程（谁改了什么怎么办）

1. 改任何工件 → `m5_manifest.py check` FAIL（漂移 + release_hash 实时重算不一致）。
2. 改 release-spec.json（版本/批准/冻结）→ check 报 spec 不一致 → 重跑 build。
3. 重跑 `m5_manifest.py build` → 新候选（UNAPPROVED 需重新 GATE；同 release_hash 的
   合法批准可核验）→ 生成新 ReleaseCurrent.lean。
4. `python3 scripts/verify_all.py christmas-buddy` 一键全链（含两轮收敛与生成+治理测试）。
