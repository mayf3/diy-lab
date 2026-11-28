# ADR-001：是否抽象共享 Manufacturing Release 原语（进 primitives）

状态：**ACCEPTED-DEFERRED**（先两项目用例验证，暂不进 primitives）

## 背景
Space Buddy R1 用 `R1.<pcb>.<cad>.<fw>.<bom>` 四元组（文档+工作台 catalog 校验）；Christmas Buddy Batch3 用 Release 候选 + manifest_hash + approval_state + Lean 合同 + 对抗测试。两处语义重叠：四段完整性、变更即新候选、人工批准门禁、工件-哈希绑定。

## 共同语义（若抽象，应包含）
四元组完整性 / 任一分项变化 → 新候选 / 旧批准不继承 / 人工 GATE 批准 / NOT_YET 不带哈希。

## 差异
Space Buddy 版本号是字符串四段（人读）；Christmas Buddy 是 Option Nat + 真实文件哈希绑定 + Lean 定理。工件扩展不同（Space Buddy 无 Lean/无 NOT_YET 登记）。

## 决定
暂不抽象：只有一个项目实现了带哈希绑定的完整合同（n=1 的通用化风险）；Space Buddy 的实现是文档级校验，强行统一会迫使对方迁移。**触发再评估条件**：第三个硬件项目立项，或 Space Buddy 进入真实制造包阶段。届时以两个真实用例提炼 primitives 原语，走 primitives 仓库的 Model Challenge/PR 流程。
