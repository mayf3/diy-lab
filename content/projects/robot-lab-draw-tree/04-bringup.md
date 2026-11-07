# G3｜在 Mac 上第一次连接 LeRobot

## 目标

识别串口、为从臂配置唯一电机 ID、完成官方校准和**全程看护下的低速空载动作测试**。这一关不带笔、不画纸。

## 准备

- 已固定在桌上的 SO-101 follower、独立断电手段、USB 数据线、核准的电源。
- Python 虚拟环境；[LeRobot SO-101 官方命令](https://huggingface.co/docs/lerobot/so101)；[LeRobot 安装](https://huggingface.co/docs/lerobot/installation)。
- 清空机械臂周围工作区，人手与儿童不得进入机械臂运动范围。**禁止通电后边运动边安装零件。**

## 操作

1. 在 Mac Terminal 中建立隔离环境，装官方所需的 Feetech 驱动。**不同版本 LeRobot 命令会变，执行前核对官方当日文档并记录版本。**

```bash
python3 -m venv .venv-robot
source .venv-robot/bin/activate
python -m pip install --upgrade pip
python -m pip install "lerobot[feetech]"
python -m pip show lerobot
```

2. 把驱动板 USB 连 Mac，接入**G1 已确认正确**的电源，先运行 `lerobot-find-port`，记录输出的串口名；示例可能是 `/dev/tty.usbmodem...`，**不可直接复制别人机器上的端口**。
3. 用官方 `lerobot-setup-motors`（类型 `so101_follower`）逐台设置电机 ID 和通信参数，**未配置的舵机每次只接一只**；设置完做 F1–F6 标签并核对对应关节。不同安装版若无该 CLI，使用官方文档的等价 API，不要猜子命令。
4. 全部机械装妥、清理活动范围后，按官方教程先放在关节中间位置，运行从臂校准命令（将示例串口替换成你实际得到的值）：

```bash
lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/tty.usbmodem_REPLACE_ME --robot.id=robot_lab_follower
```

5. 校准成功后，将校准文件备份到私人实验目录（不要提交真实 USB 设备标识）。通过官方 Python API **只读获取当前关节状态**，核对电机数量、角度合理性，再按说明制作小幅、低速、已确认工作区内的动作测试。
6. **不要把示例角度生搬硬套**。让 Codex 基于当前已安装的 LeRobot Python API 编写 `safe_jog`：先读取实际状态，再限幅、限速、检查轨迹和超时，看护人员按确认后才发一小步动作；每一步能中止。
7. 记录 LeRobot 版本、Python 版本、端口识别（脱敏）、校准是否成功、首次运动是否异响或过热，以及急停/断电可触及性。

## 验收

- [ ] 实际 USB 串口能找到，六个电机 ID 唯一并与关节一致。
- [ ] 官方校准正常完成，日志保存；设备状态可读。
- [ ] 在监督下完成**不带笔**的小幅动作，能够立即中止；异常时不上 G4。

## 出问题怎么办

- 未发现串口：检查 USB 数据线和驱动板、用 `ls /dev/tty.*` 辅助找设备。
- 电机不响应：先断电；确认外接电源，而不是误认为 USB 足以驱动舵机。
- 电机号错/错齿比：停止，回到 G1 和逐台 ID 设置，不要通过调大运动范围硬闯。
- 运动时卡滞、异常声响、冒烟或发热：立即使用独立断电手段，查清硬件后才能再次上电。

**下一关**：[G4 纸面和笔架](/projects/robot-lab-draw-tree/05-draw-workspace/)。
