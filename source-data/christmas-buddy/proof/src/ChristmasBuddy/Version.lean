/-!
# Christmas Buddy V1 · M5 制造模型（版本四元组）

延续 Space Buddy R1 建立的版本四元组惯例（pcb.cad.fw.bom），定义：
- `Release`：pcb / cad / fw / bom 四个版本槽。
- `complete`：四段全部存在。
- `isFrozen`：属于已冻结发布清单。
- `manufacturable`：complete 且 frozen。

证明：
- `thm_frozen_are_complete`：frozen 清单中的发布都完整。
- `thm_incomplete_never_manufacturable`：四段不齐的发布永不可制造（安全门禁）。
- `thm_frozen_manufacturable`：frozen 发布都可进入制造流程。
- `thm_complete_sound`：complete 判定与逐段 isSome 合取等价。
- v5（Batch4.2）：制造资格 = 完整 + 冻结 + 批准人身份精确一致（r.approver = some
  rec.approver）+ 记录批准人非空 + release/manifest_hash 精确一致 + 注册表成员
  （`manufacturingReleaseIn`，注册表为显式输入）；身份不符 / 空批准人 / 未登记 /
  空注册表均不可制造，精确登记则可制造。

实现对应（MAP）：`m5_manifest.py` 计算 design-to-artifact 的 sha256 追溯；
本文件只证结构规则；哈希一致性由脚本检查并登记为 TESTED 证据，
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

/-- 已冻结发布清单（当前只含 v1 占位；真实清单由 m5_manifest.py 生成）。 -/
def frozenList : List Release := [v1]

/-- 属于冻结清单（用 decide 等价，便于无依赖证明）。 -/
def isFrozen (r : Release) : Bool :=
  frozenList.any (fun x => decide (x = r))

/-- 可进入制造流程 = 完整且已冻结。 -/
def manufacturable (r : Release) : Bool :=
  complete r && isFrozen r

/-- frozen 清单中的每个发布都完整。 -/
theorem thm_frozen_are_complete : ∀ r, isFrozen r = true → complete r = true := by
  intro r h
  have hun : isFrozen r = decide (v1 = r) := by
    simp [isFrozen, frozenList, List.any]
  rw [hun] at h
  cases hr : decide (v1 = r) with
  | false =>
    rw [hr] at h
    simp at h
  | true =>
    simp at hr
    rw [← hr]
    rfl

/-- 不完整的发布绝不可制造（安全门禁）。 -/
theorem thm_incomplete_never_manufacturable :
    ∀ r : Release, complete r = false → manufacturable r = false := by
  intro r hc
  simp [manufacturable, hc]

/-- frozen 发布都可进入制造流程。 -/
theorem thm_frozen_manufacturable :
    ∀ r, isFrozen r = true → manufacturable r = true := by
  intro r h
  have hc : complete r = true := thm_frozen_are_complete r h
  simp [manufacturable, hc, h]

/-- complete 判定与逐段 isSome 合取逐条等价。 -/
theorem thm_complete_sound :
    ∀ r : Release,
      complete r = true ↔ r.pcb.isSome ∧ r.cad.isSome ∧ r.fw.isSome ∧ r.bom.isSome := by
  intro r
  cases r with
  | mk pcb cad fw bom =>
    cases pcb <;> cases cad <;> cases fw <;> cases bom <;>
      simp [complete]


/-! ### v2/v4/v5 扩展：批准记录绑定（release + manifest_hash + approver 身份 + 注册表成员） -/

/-- 候选 + 批准人（Option String：none=未批准）。 -/
structure ApprovedRelease where
  release : Release
  approver : Option String
  deriving DecidableEq, Repr

/-- 批准记录：绑定**精确** release、该候选的 manifest_hash、批准人——缺一不可。 -/
structure ApprovalRecord where
  release : Release
  manifestHash : String
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

/-- 制造许可（Batch4.2 全判定，注册表为**显式输入**）：
    完整 + 冻结 + 候选批准人非空 + **批准人身份精确一致**（r.approver = some rec.approver，
    P0-1 #4727196821）+ 记录批准人非空串 + release 精确一致 + manifest_hash 精确一致
    + 批准记录属于受信任注册表（P1-1）。 -/
def manufacturingReleaseIn (registry : List ApprovalRecord)
    (r : ApprovedRelease) (rec : ApprovalRecord) (currentHash : String) : Bool :=
  complete r.release && isFrozen r.release
    && r.approver.isSome && decide (r.approver = some rec.approver)
    && decide (rec.approver.isEmpty = false)
    && decide (rec.release = r.release) && decide (rec.manifestHash = currentHash)
    && registry.any (fun x => decide (x = rec))

/-- 默认制造许可 = 受控生产注册表（当前为空）上的判定。 -/
def manufacturingRelease (r : ApprovedRelease) (rec : ApprovalRecord) (currentHash : String) : Bool :=
  manufacturingReleaseIn approvedRegistry r rec currentHash

/-- 未批准（approver 为空）不可制造。 -/
theorem thm_unapproved_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      r.approver.isSome = false → manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h happro
  simp [manufacturingReleaseIn, happro]

/-- 批准记录的 manifest_hash 与当前候选不一致 → 不可制造（旧批准不越哈希）。 -/
theorem thm_approval_hash_mismatch_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      rec.manifestHash ≠ h → manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h hne
  by_cases hpx : rec.manifestHash = h
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- 批准记录绑定不同 release → 不可制造。 -/
theorem thm_approval_release_mismatch_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      rec.release ≠ r.release → manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h hne
  by_cases hpx : rec.release = r.release
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- P0-1：候选批准人与记录批准人身份不一致 → 不可制造（其余字段再精确也不行）。 -/
theorem thm_approver_identity_mismatch_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      r.approver ≠ some rec.approver → manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h hne
  by_cases hpx : r.approver = some rec.approver
  · exact absurd hpx hne
  · simp [manufacturingReleaseIn, hpx]

/-- 空字符串批准人不可制造（身份一致也不行：空标识不是有效批准人）。 -/
theorem thm_empty_approver_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      rec.approver.isEmpty = true → manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h hempty
  have hd : decide (rec.approver.isEmpty = false) = false := by simp [hempty]
  simp [manufacturingReleaseIn, hd]

/-- P1-1：字段全部正确但批准记录未登记于注册表 → 不可制造。 -/
theorem thm_unregistered_record_not_manufacturable :
    ∀ registry : List ApprovalRecord, ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      registry.any (fun x => decide (x = rec)) = false →
      manufacturingReleaseIn registry r rec h = false := by
  intro registry r rec h hnot
  simp [manufacturingReleaseIn, hnot]

/-- P1-1：空注册表（生产现状）下任何候选都不可制造。 -/
theorem thm_empty_registry_not_manufacturable :
    ∀ r : ApprovedRelease, ∀ rec : ApprovalRecord, ∀ h : String,
      manufacturingReleaseIn [] r rec h = false := by
  intro r rec h
  simp [manufacturingReleaseIn, List.any]

/-- P1-1 正向：完整 + 冻结 + 批准人精确一致 + 已注册 → 可制造（合同不是恒假开关）。 -/
theorem thm_registered_exact_approval_manufacturable :
    manufacturingReleaseIn [⟨v1, "h", "GATE"⟩] ⟨v1, some "GATE"⟩ ⟨v1, "h", "GATE"⟩ "h" = true := by
  rfl

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

/- UNPROVEN 义务登记（OB-4）：manifest_hash 对内容碰撞的抵抗力不可在 Lean 内证明
    （需要 SHA-256 抗碰撞性），由 Python 对抗矩阵 A1-A12 在真实文件层承担。 -/
end ChristmasBuddy.Version
