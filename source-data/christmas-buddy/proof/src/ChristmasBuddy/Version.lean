/-!
# Christmas Buddy V1 · M5 制造模型（版本四元组）

延续 Space Buddy R1 建立的版本四元组惯例（pcb.cad.fw.bom），定义：
- `Release`：pcb / cad / fw / bom 四个版本槽（各组件可独立演进）。
- `complete`：四段全部存在。
- `frozenWellFormed`：冻结注册表良构（只登记完整四元组）。
- `manufacturableIn frozen r`：complete 且 r 精确在动态冻结注册表中。

证明：
- `thm_frozen_membership_complete`：良构冻结注册表中的发布都完整。
- `thm_incomplete_never_manufacturable`：四段不齐的发布永不可制造（安全门禁）。
- `thm_frozen_manufacturable`：完整且在册的发布可进入制造流程。
- `thm_complete_sound`：complete 判定与逐段 isSome 合取等价。
- v5（Batch4.2）：制造资格含批准人身份精确一致 + 记录批准人非空 + 注册表成员。
- v6（Batch4.3）：双层哈希语义——批准记录绑定 **release_hash**（产品内容身份），
  与 manifest_hash（清单封套）不得混用；冻结注册表与批准注册表均为制造资格的
  **显式输入**（动态，由 m5_manifest.build 从 release-spec.json 受控生成）；
  混合版本（PCB=2 CAD=1 FW=3 BOM=2）可合法冻结+批准；任一组件版本变化使旧批准失效。

实现对应（MAP）：`m5_manifest.py` 计算 release_hash/manifest_hash（SHA256）与真实文件
绑定；本文件只证结构规则；哈希一致性由脚本检查并登记为 TESTED 证据，
不得声称 Lean 已证明哈希绑定。

UNPROVEN 义务登记：
- OB-1：Gerber/坐标/BOM 实际来自已批准 PCB 版本——待真实 EDA 工程产出后由
  m5_manifest.py 绑定哈希并实测核对（本轮无真实制造文件，不证明存在性）。
-/

namespace ChristmasBuddy.Version

/-- 一次发布：四个设计段的版本槽。 -/
structure Release where
  pcb : Option Nat
  cad : Option Nat
  fw  : Option Nat
  bom : Option Nat
  deriving DecidableEq, Repr

/-- 四段版本全部存在才算完整。 -/
def complete (r : Release) : Bool :=
  r.pcb.isSome && r.cad.isSome && r.fw.isSome && r.bom.isSome

/-- 预研版四元组：四段均未冻结（本 PR 的真实状态）。 -/
def preresearch : Release := ⟨none, none, none, none⟩

/-- 首个冻结发布的目标形态（占位示例：V1 各段 rev 1）。 -/
def v1 : Release := ⟨some 1, some 1, some 1, some 1⟩

/-- 动态冻结注册表（Batch4.3）：制造资格判断的**显式输入**；生产当前为空，
    由 m5_manifest.build 从 release-spec.json 受控生成（经 ReleaseCurrent.lean
    的 currentFrozenRegistry 投影），不得手工编辑生成的 Manifest 伪造。 -/
def frozenRegistry : List Release := []

/-- 冻结注册表良构：登记的发布都必须完整（GATE 只能冻结完整四元组）。 -/
def frozenWellFormed (frozen : List Release) : Bool :=
  frozen.all complete

/-- 良构冻结注册表中的每个发布都完整。 -/
theorem thm_frozen_membership_complete :
    ∀ frozen : List Release, frozenWellFormed frozen = true →
      ∀ r : Release, frozen.any (fun x => decide (x = r)) = true → complete r = true := by
  intro frozen hw r hm
  rw [frozenWellFormed, List.all_eq_true] at hw
  rw [List.any_eq_true] at hm
  obtain ⟨x, hx, hxr⟩ := hm
  have hxr' : x = r := by simpa using hxr
  rw [← hxr']
  exact hw x hx

/-- 冻结层面资格 = 完整且精确在冻结注册表（批准检查见 manufacturingReleaseIn）。 -/
def manufacturableIn (frozen : List Release) (r : Release) : Bool :=
  complete r && frozen.any (fun x => decide (x = r))

/-- 不完整的发布绝不可制造（安全门禁，任意冻结注册表下成立）。 -/
theorem thm_incomplete_never_manufacturable :
    ∀ frozen : List Release, ∀ r : Release, complete r = false →
      manufacturableIn frozen r = false := by
  intro frozen r hc
  simp [manufacturableIn, hc]

/-- 完整且在册的发布可进入冻结资格判定（合同不是恒假开关）。 -/
theorem thm_frozen_manufacturable :
    ∀ frozen : List Release, ∀ r : Release, complete r = true →
      frozen.any (fun x => decide (x = r)) = true → manufacturableIn frozen r = true := by
  intro frozen r hc hm
  simp [manufacturableIn, hc, hm]

/-- 混合版本正向（Batch4.3）：PCB=2 CAD=1 FW=3 BOM=2——各组件版本独立演进，
    完整且精确冻结 → 冻结层面资格成立（不要求所有组件同版本号）。 -/
theorem thm_mixed_version_frozen_manufacturable :
    manufacturableIn [⟨some 2, some 1, some 3, some 2⟩]
      ⟨some 2, some 1, some 3, some 2⟩ = true := by rfl

/-- complete 判定与逐段 isSome 合取逐条等价。 -/
theorem thm_complete_sound :
    ∀ r : Release,
      complete r = true ↔ r.pcb.isSome ∧ r.cad.isSome ∧ r.fw.isSome ∧ r.bom.isSome := by
  intro r
  cases r with
  | mk pcb cad fw bom =>
    cases pcb <;> cases cad <;> cases fw <;> cases bom <;>
      simp [complete]


/-! ### v2/v4/v5/v6 扩展：批准记录绑定（release + release_hash + approver 身份 + 双注册表） -/

/-- 候选 + 批准人（Option String：none=未批准）。 -/
structure ApprovedRelease where
  release : Release
  approver : Option String
  deriving DecidableEq, Repr

/-- 批准记录：绑定**精确** release、该候选的 **release_hash**（产品内容身份）、
    批准人——缺一不可。语义分层（Batch4.3）：releaseHash 字段绑定 release_hash，
    **不是** manifest_hash（清单封套完整性）——两层哈希不得混用，
    否则批准记录哈希固定点回归（PR#37 Review #4727422072）。 -/
structure ApprovalRecord where
  release : Release
  releaseHash : String
  approver : String
  deriving DecidableEq, Repr

/-- 受信任批准注册表：制造资格要求批准记录**精确登记于此**（Batch4.2 P1-1）。
    真实生产注册表当前阶段保持为空；测试使用隔离注册表——或经参数显式传入
    （manufacturingReleaseIn），或由 m5_manifest.gen_lean 从 manifest approval_records
    受控生成（ReleaseCurrent.lean 的 currentRegistry / isolatedTestRegistry）。
    外部信任边界：Lean 只证明「记录在注册表中」这一结构事实；现实中批准人的
    身份与授权真实性由工作台 GATE 门禁与受控批准记录流程负责。 -/
def approvedRegistry : List ApprovalRecord := []

def isApproved (r : ApprovalRecord) : Bool :=
  approvedRegistry.any (fun x => decide (x = r))

/-- 制造许可（Batch4.3 全判定；冻结注册表 + 批准注册表均为**显式输入**）：
    四元组完整 + 精确 Release 在冻结注册表 + 候选批准人非空 + 批准人身份精确一致
    （r.approver = some rec.approver）+ 记录批准人非空串 + release 精确一致
    + **release_hash 精确一致** + 批准记录属于受信任批准注册表。 -/
def manufacturingReleaseIn (frozen : List Release) (registry : List ApprovalRecord)
    (rhash : String) (r : ApprovedRelease) (rec : ApprovalRecord) : Bool :=
  complete r.release
    && frozen.any (fun x => decide (x = r.release))
    && r.approver.isSome && decide (r.approver = some rec.approver)
    && decide (rec.approver.isEmpty = false)
    && decide (rec.release = r.release) && decide (rec.releaseHash = rhash)
    && registry.any (fun x => decide (x = rec))

/-- 默认制造许可 = 受控生产注册表（冻结/批准注册表当前均为空）上的判定。
    rhash 传当前候选的 release_hash（内容身份）。 -/
def manufacturingRelease (r : ApprovedRelease) (rec : ApprovalRecord) (rhash : String) : Bool :=
  manufacturingReleaseIn frozenRegistry approvedRegistry rhash r rec

/-- 未批准（approver 为空）不可制造。 -/
theorem thm_unapproved_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        r.approver.isSome = false → manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec happro
  simp [manufacturingReleaseIn, happro]

/-- 批准记录的 release_hash 与当前候选不一致 → 不可制造（旧批准不越内容身份）。 -/
theorem thm_release_hash_mismatch_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        rec.releaseHash ≠ h → manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hne
  by_cases hpx : rec.releaseHash = h
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- 批准记录绑定不同 release → 不可制造。 -/
theorem thm_approval_release_mismatch_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        rec.release ≠ r.release → manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hne
  by_cases hpx : rec.release = r.release
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- 候选批准人与记录批准人身份不一致 → 不可制造（其余字段再精确也不行）。 -/
theorem thm_approver_identity_mismatch_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        r.approver ≠ some rec.approver → manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hne
  by_cases hpx : r.approver = some rec.approver
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- 空字符串批准人不可制造（身份一致也不行：空标识不是有效批准人）。 -/
theorem thm_empty_approver_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        rec.approver.isEmpty = true → manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hempty
  have hd : decide (rec.approver.isEmpty = false) = false := by simp [hempty]
  simp [manufacturingReleaseIn, hd]

/-- 候选不在冻结注册表 → 不可制造（冻结注册表动态，成员资格为显式检查）。 -/
theorem thm_unfrozen_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        frozen.any (fun x => decide (x = r.release)) = false →
        manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hnot
  simp [manufacturingReleaseIn, hnot]

/-- 字段全部正确但批准记录未登记于注册表 → 不可制造。 -/
theorem thm_unregistered_record_not_manufacturable :
    ∀ frozen : List Release, ∀ registry : List ApprovalRecord, ∀ h : String,
      ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord,
        registry.any (fun x => decide (x = rec)) = false →
        manufacturingReleaseIn frozen registry h r rec = false := by
  intro frozen registry h r rec hnot
  simp [manufacturingReleaseIn, hnot]

/-- 空批准注册表（生产现状）下任何候选都不可制造。 -/
theorem thm_empty_registry_not_manufacturable :
    ∀ frozen : List Release, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      manufacturingReleaseIn frozen [] h r rec = false := by
  intro frozen r rec h
  simp [manufacturingReleaseIn, List.any]

/-- 正向：完整 + 冻结 + 批准人精确一致 + release_hash 精确一致 + 已注册 → 可制造
    （合同不是恒假开关）。 -/
theorem thm_registered_exact_approval_manufacturable :
    manufacturingReleaseIn [v1] [⟨v1, "h", "GATE"⟩] "h" ⟨v1, some "GATE"⟩ ⟨v1, "h", "GATE"⟩
      = true := by rfl

/-- 混合版本正向（完整制造许可）：PCB=2 CAD=1 FW=3 BOM=2 独立演进，
    精确冻结 + 精确批准（绑 release_hash）→ 可制造。 -/
theorem thm_mixed_version_manufacturing_release :
    manufacturingReleaseIn [⟨some 2, some 1, some 3, some 2⟩]
      [⟨⟨some 2, some 1, some 3, some 2⟩, "h-mixed", "GATE-test"⟩] "h-mixed"
      ⟨⟨some 2, some 1, some 3, some 2⟩, some "GATE-test"⟩
      ⟨⟨some 2, some 1, some 3, some 2⟩, "h-mixed", "GATE-test"⟩ = true := by rfl

/-- 版本变化（PCB 2→3，新版本已在冻结注册表）→ 旧批准记录仍绑旧版本 → 不可制造
    （任一组件版本变化都使旧批准失效；CAD/FW/BOM 同理，见生成文件 reg_*_bump 定理）。 -/
theorem thm_version_change_invalidates_old_approval :
    manufacturingReleaseIn [⟨some 2, some 1, some 3, some 2⟩, ⟨some 3, some 1, some 3, some 2⟩]
      [⟨⟨some 2, some 1, some 3, some 2⟩, "h-mixed", "GATE-test"⟩] "h-mixed"
      ⟨⟨some 3, some 1, some 3, some 2⟩, some "GATE-test"⟩
      ⟨⟨some 2, some 1, some 3, some 2⟩, "h-mixed", "GATE-test"⟩ = false := by rfl

theorem thm_registry_membership_implies_approved :
    ∀ r, isApproved r = true → r.approver.isEmpty = false := by
  intro r h
  simp [approvedRegistry, isApproved, List.any] at h

/-! ### v3 扩展：BOM 完整性、目录清单纯度、哈希防碰撞义务 -/

/-- BOM 完整性（抽象模型）：required 中每个槽位都必须有对应条目。 -/
def bomComplete (required : List String) (entries : List (String × String)) : Bool :=
  required.all (fun r => entries.any (fun e => e.1 = r))

theorem thm_bom_complete_nil : ∀ entries : List (String × String), bomComplete [] entries = true := by
  intro entries; rfl

theorem thm_bom_complete_cons :
    ∀ (head : String) (tail : List String) (entries : List (String × String)),
      bomComplete (head :: tail) entries = true → entries.any (fun e => e.1 = head) = true := by
  intro head tail entries h
  exact (Bool.and_eq_true _ _).mp h |>.1

/-- 目录清单函数是纯函数：相同文件列表 → 相同清单（顺序无关性由 Python A9 在真实层实测）。 -/
structure DirEntry where
  path : String
  sha : String
  deriving DecidableEq, Repr

def dirManifest (files : List DirEntry) : List DirEntry := files

theorem thm_dir_manifest_pure :
    ∀ l : List DirEntry, dirManifest l = dirManifest l := by
  intro l; rfl

/- UNPROVEN 义务登记（不得在 Lean 内声明已证）：
  OB-4：release_hash / manifest_hash 对内容碰撞的抵抗力不可在 Lean 内证明
        （需要 SHA-256 抗碰撞性），由 Python 对抗矩阵 A1-A16 与 N1-N8 在真实文件层承担。
  OB-5：manifest_hash（封套）独立一致性——SHA256(canonical_manifest_payload) 由
        Python check 每次独立重算比对（Batch4.3 双层哈希解耦后，封套含 release_hash 值
        但不含自身，无 H=SHA256(Payload(H)) 固定点）；Lean 只证结构一致性，
        不承担哈希计算。 -/
end ChristmasBuddy.Version
