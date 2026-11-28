# Christmas Buddy V1 装配验证（真实布尔求交 + 导出 STEP 几何复核）

查看日期：2026-11-28｜工具：CadQuery 2.8 / OCCT（开孔检查在重导入的最终 STEP 上以探针求交验证）

说明：头部内腔与眼睛模组舱在下一 CAD 轮细化；未建模功能一律登记 UNKNOWN，不冒充 PASS。

## 方案 A
- **PASS** — 总高在 120–160mm：z_max=139.5mm〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核全部位于体部内腔：内腔外体积 0.000mm³（阈值 5）〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 前后壳 ≈ ∅：干涉体积 0.000mm³（阈值 5）〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 头部 ≈ ∅：干涉体积 0.000mm³〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 帽 ≈ ∅：干涉体积 0.000mm³〔parametric/boolean（建模实体）〕
- **PASS** — Pi 迭放弦长净空（Pi 65mm @偏距 8.6mm）：全程满足 + 2×1.0mm 间隙〔parametric/boolean（建模实体）〕
- **PASS** — PCB 站立弦长净空（58mm）：全程满足 + 2×1.0mm 间隙〔parametric/boolean（建模实体）〕
- **PASS** — PCB 槽公差链（临界项）：槽宽 2.0mm vs PCB 1.6 + 2×0.2 打印公差 = 2.0mm——临界，打印轮实测后冻结〔parametric/boolean（建模实体）〕
- **PASS** — 格栅 16 槽全部贯穿（重导入 STEP）：全部贯穿〔geometry(exported STEP)〕
- **PASS** — 格栅实测开孔面积 ≥ 60% 振膜（局部坐标采样测量）：实测 400mm² ≥ 需求 369mm²（369）〔geometry(exported STEP)〕
- **PASS** — USB-C 开孔贯穿（重导入 STEP）：探针干涉体积 0.000mm³〔geometry(exported STEP)〕
- **PASS** — USB 插头包络与壳体零碰撞：包络干涉 0.000mm³（含开孔通道豁免区外）〔geometry(exported STEP)〕
- **PASS** — 麦克风声孔贯穿（重导入 STEP）：探针干涉体积 0.000mm³〔geometry(exported STEP)〕
- **UNKNOWN** — 眼窗开孔与扩散板：头部内腔与眼窗未在本轮 CAD 建模（下一 CAD 轮）
- **UNKNOWN** — 星星灯透光窗：前壳透光缩壁未建模（下一 CAD 轮）
- **UNKNOWN** — 麦克风声学密封圈与后腔：密封件未建模，声学性能不可据此判定（声学轮）
- **UNKNOWN** — 打印公差 0.2mm：ASSUMPTION，试打印实测后解除（OB-2）（试打印）
- **UNKNOWN** — 螺丝柱/加强筋：本轮壳体未建柱筋，装配强度未知（T-MEC）

## 方案 B
- **PASS** — 总高在 120–160mm：z_max=145.7mm〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核全部位于体部内腔：内腔外体积 0.000mm³（阈值 5）〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 前后壳 ≈ ∅：干涉体积 0.000mm³（阈值 5）〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 头部 ≈ ∅：干涉体积 0.000mm³〔parametric/boolean（建模实体）〕
- **PASS** — 功能内核 ∩ 帽 ≈ ∅：干涉体积 0.000mm³〔parametric/boolean（建模实体）〕
- **PASS** — Pi 迭放弦长净空（Pi 65mm @偏距 8.6mm）：全程满足 + 2×1.0mm 间隙〔parametric/boolean（建模实体）〕
- **PASS** — PCB 站立弦长净空（58mm）：全程满足 + 2×1.0mm 间隙〔parametric/boolean（建模实体）〕
- **PASS** — PCB 槽公差链（临界项）：槽宽 2.0mm vs PCB 1.6 + 2×0.2 打印公差 = 2.0mm——临界，打印轮实测后冻结〔parametric/boolean（建模实体）〕
- **PASS** — 格栅 16 槽全部贯穿（重导入 STEP）：全部贯穿〔geometry(exported STEP)〕
- **PASS** — 格栅实测开孔面积 ≥ 60% 振膜（局部坐标采样测量）：实测 400mm² ≥ 需求 369mm²（369）〔geometry(exported STEP)〕
- **PASS** — USB-C 开孔贯穿（重导入 STEP）：探针干涉体积 0.000mm³〔geometry(exported STEP)〕
- **PASS** — USB 插头包络与壳体零碰撞：包络干涉 0.000mm³（含开孔通道豁免区外）〔geometry(exported STEP)〕
- **PASS** — 麦克风声孔贯穿（重导入 STEP）：探针干涉体积 0.000mm³〔geometry(exported STEP)〕
- **UNKNOWN** — 眼窗开孔与扩散板：头部内腔与眼窗未在本轮 CAD 建模（下一 CAD 轮）
- **UNKNOWN** — 星星灯透光窗：前壳透光缩壁未建模（下一 CAD 轮）
- **UNKNOWN** — 麦克风声学密封圈与后腔：密封件未建模，声学性能不可据此判定（声学轮）
- **UNKNOWN** — 打印公差 0.2mm：ASSUMPTION，试打印实测后解除（OB-2）（试打印）
- **UNKNOWN** — 螺丝柱/加强筋：本轮壳体未建柱筋，装配强度未知（T-MEC）

