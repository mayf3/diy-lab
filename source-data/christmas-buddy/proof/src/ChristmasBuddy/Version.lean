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


/-! ### v2 扩展：批准状态与「不静默继承」合同 -/

/-- Release 增加批准维度：批准人（Option String，none=未批准）。 -/
structure ApprovedRelease where
  release : Release
  approver : Option String
  deriving DecidableEq, Repr

/-- 制造许可 = 完整 + 冻结 + 已批准（三重门禁，缺一不可）。 -/
def manufacturingRelease (r : ApprovedRelease) : Bool :=
  complete r.release && isFrozen r.release && r.approver.isSome

/-- 未批准的候选不可制造（GATE 门禁的形式化）。 -/
theorem thm_unapproved_not_manufacturable :
    ∀ r : ApprovedRelease, r.approver = none → manufacturingRelease r = false := by
  intro r h
  simp [manufacturingRelease, h]

/-- 批准绑定精确版本：同一工件集合的批准记录是确定的。 -/
def approvedRegistry : List ApprovedRelease := []

/-- 注册表成员判定（decide 等价，无依赖证明）。 -/
def isApproved (r : ApprovedRelease) : Bool :=
  approvedRegistry.any (fun x => decide (x = r))

/-- 注册表中的每条批准都满足三重门禁的前两条（complete+frozen 由登记流程保证；
    本定理证：注册表成员的 approver 必为 some——登记即批准）。 -/
theorem thm_registry_membership_implies_approved :
    ∀ r, isApproved r = true → r.approver.isSome = true := by
  intro r h
  -- 注册表为空时前提即为 False，simp 直接闭合目标
  simp [approvedRegistry, isApproved, List.any] at h

/-- 任一分项变化必须形成新候选：Release 值相等当且仅当四段逐一相等
    （因此任何一段变化都产生 ≠ 旧值的新 Release，注册表不会自动包含它）。 -/
theorem thm_release_ext :
    ∀ a b : Release,
      a = b ↔ a.pcb = b.pcb ∧ a.cad = b.cad ∧ a.fw = b.fw ∧ a.bom = b.bom := by
  intro a b
  cases a <;> cases b <;> simp

end ChristmasBuddy.Version
