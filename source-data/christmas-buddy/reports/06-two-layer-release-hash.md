# 双层哈希规范（Batch4.3 · 双层 Release 哈希模型）

修复 PR #37 Review #4727422072：旧模型中 `canonical_payload` 含 `approval_records`，
而每条 `ApprovalRecord.manifest_hash` 又要求等于候选 `manifest_hash`，形成
`H = SHA256(Payload(H))` 固定点——**合法批准记录无法实际生成**。

## 一、两层定义（唯一实现：m5_manifest.py v6）

### 1. Release Content Hash（内容身份层）

```
release_hash = SHA256( canonical_release_payload )
canonical_release_payload = {
  artifacts,                      # 逐工件 sha256；目录工件 = files+skipped_symlinks（全按完整相对路径排序）
  release: { product, version_tuple, source_commit },
  not_yet,                        # 按完整相对路径排序
}
```

- 含义：**产品发布内容的身份**。任何工件或四元组变化 → release_hash 变化 → 旧批准失效。
- **不得包含**：`approval_state` / `approver` / `approval_records` / `manifest_hash` / `release_hash`
  （批准元数据与循环字段一律不入）。

### 2. Manifest Envelope Hash（清单封套层）

```
manifest_hash = SHA256( canonical_manifest_payload )
canonical_manifest_payload = {
  release_hash,                   # 内容身份的绑定值
  frozen_registry,                # 动态冻结注册表（语义无序，按 JSON 规范形式排序）
  approval_state, approver, approval_records,   # 记录按 JSON 规范形式排序
}
```

- 含义：**完整发布清单的完整性**。release_hash / 批准状态 / 批准人 / 批准记录 / 冻结注册表
  任一变化 → manifest_hash 变化。
- **不含 manifest_hash 自身**——无自引用、无固定点。

## 二、批准绑定语义（不得混用）

| 字段 | 语义 | 使用者 |
|---|---|---|
| `release_hash` | 产品内容身份；**批准记录 `releaseHash` 绑定本值** | Lean `ApprovalRecord.releaseHash`、`approval_consistency` 精确匹配、gen_lean `currentReleaseHash` |
| `manifest_hash` | 清单封套完整性；篡改检测 | check 封套重算、gen_lean `currentManifestHash`（仅身份展示，不入判定） |

`ApprovalRecord = { release, releaseHash, approver }`——Lean 侧字段已从
`manifestHash` 更名 `releaseHash`（Version.lean v6），防止两层混用。

## 三、性质（由测试证明，非口头声明）

1. **无循环依赖**：release_hash 输入不含任何批准元数据（gen 测试「解环」案例：批准元数据
   变化 → release_hash 逐位稳定、manifest_hash 变化；用空工件集直接验证 approval_* 键不入基线）。
2. **合法批准可实际生成**：POS-B 全链（spec 定版 → build 取 release_hash → 记录绑定该值 →
   重建 → release_hash 不变、manifest_hash 变化 → **M5.check PASS** → Lean 编译 PASS →
   公理审计 PASS）。旧模型下此流程在数学上不可完成。
3. **旧批准不越内容**：工件/四元组变化 → 实时重算 release_hash ≠ 登记 → FAIL（N2/N3/N5）；
   记录绑定旧 release_hash → 精确匹配失败（N1）。
4. **封套完整性**：批准状态/批准人/记录/冻结注册表任一变化 → manifest_hash 变（N4/N6/N8；
   手改登记值 → 重算不一致 FAIL，N7）。
5. **确定性**：canonical 实现为 build/check 共用的唯一函数；数组全规范化
   （含符号链接完整路径序，PR#36 Review #4727196824 的 A14 回归保留）。

## 四、release-spec.json（受控版本输入）

- build 的唯一版本来源：tuple / frozen_registry / approval_state / approver / approval_records
  （不再在代码中硬编码空四元组）；新候选默认 UNAPPROVED。
- **不进 ARTIFACT_TABLE**：批准元数据不得进入 release_hash 基线（否则固定点回归）；
  其完整性由 check 的 spec↔manifest 一致性比对承担（手改生成的 manifest 伪造冻结版本 → 不一致 FAIL）。
- 真实生产批准必须经工作台 GATE；`approval_records` 生产保持 `[]`。

## 五、三层分工（不得混淆）

| 层 | 职责 | 证据类型 |
|---|---|---|
| Lean（Version.lean） | 抽象合同与结构一致性（成员资格、精确匹配、失效传播） | PROVEN（公理白名单审计） |
| Python（m5_manifest.py） | SHA256 计算、真实文件绑定、实时重算、封套完整性 | TESTED（正/负向实测） |
| 工作台 GATE | 现实中批准人的身份与授权真实性 | 人工流程（human-approval） |

 Lean 定理只含结构事实；manifest_hash 独立一致性义务登记为 OB-5（Version.lean 未证义务区）。
