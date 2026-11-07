# G0｜从一张纸上的树开始

## 目标

**不买任何东西**，先理解要做的实体任务，运行可复现的离线笔画校验，生成第一张 SVG 预览。约 30–60 分钟。

## 准备

- 一台可运行 Python 3.10+ 的电脑（macOS / Windows / Linux）；仓库已克隆到本地。
- 一个可写的临时目录（示例 `/tmp/robot-lab/`）。
- 无需 SO-101、GPU、API Key；此关**不接通机器人**。

## 操作

1. 进入 DIY 仓库，阅读 [SO-101 开源硬件 README](https://github.com/TheRobotStudio/SO-ARM100) 和 [LeRobot 官方 SO-101 教程](https://huggingface.co/docs/lerobot/so101)，确认不是旧的 SO-100。
2. 运行（仓库根目录执行）：

```bash
python3 source-data/robot-lab-draw-tree/plan_validator.py --self-test
mkdir -p /tmp/robot-lab
python3 source-data/robot-lab-draw-tree/plan_validator.py --plan source-data/robot-lab-draw-tree/demo_plan.json --svg /tmp/robot-lab/tree.svg
```

3. 用浏览器打开 `/tmp/robot-lab/tree.svg`：应该看到简单的树干和三角树冠。**这是纯软件计划预览，不代表机械臂可达。**
4. 用文本编辑器复制一份 `demo_plan.json`，将一处坐标改成 `1.5`；再次运行校验器，必须报错拒绝。恢复原文件，不把故意失败的版本覆盖入仓库。
5. 建私有实验目录：`~/DIY/RobotLab/{originals,working,evidence,notes}`（目录只是建议，按需创建）；不把私人照片、密钥和上游二进制文件推送到公开仓库。
6. **采购前 G0.5（必须完成）**：让 Agent / Codex 读取官方 SO-101 URDF / MJCF，在 A5 纸面上建立目标绘画区域和笔夹占位模型；检查九个采样点及树形连续路径的 IK、关节余量、路径连续性和碰撞。保存模型版本、假设、截图和报告。仓库的 plan_validator.py 只验证笔画 JSON 格式，不证明机械臂可达。
7. 若 G0.5 不能完成或结果不是 PASS，标记 BLOCKED 并停止采购；先缩小画幅、调整纸面方向或重新评估平台。只有 G0.5 PASS 后，才阅读 [采购门禁](/projects/robot-lab-draw-tree/02-purchase/)，继续核对 SKU 和电源。V1 只做细头水性笔，不做水彩。

## 验收

- [ ] `--self-test` 成功；示例生成 SVG，内容能识别为树。
- [ ] 越界笔画计划被拒绝；确认不会触发任何硬件动作。
- [ ] 知道 V1 仅做 **单臂画树**，不以自动调色或无人值守作为第一版完成条件。
- [ ] 采购前 G0.5 可达性报告已 PASS；没有报告或结果 BLOCKED 时，不进入采购。

## 出问题怎么办

- 提示 Python 不存在：先安装 Python 3.10+；不要用管理员权限乱改系统 Python。
- 提示文件找不到：确认当前目录包含 `README.md`、`source-data`。
- SVG 无法打开：检查输出路径和文件扩展名，浏览器打开即可；脚本没有联网依赖。
- 请勿为通过此关去修改机械臂零位或连接任意 USB 硬件。
- 如果官方模型无法运行、笔尖姿态无解或 IK 报告缺失，G0.5 必须保持 BLOCKED；离线 SVG 通过不能代替机械臂可达性。

**下一关**：[G1 采购核对](/projects/robot-lab-draw-tree/02-purchase/)。
