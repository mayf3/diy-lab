# G2｜让 Mac 把按键映射到 App、快捷指令和 Agent

## 目标

用可修改的**电脑端私有配置**实现一键一动作；不用每改一个会话都刷 ESP32。默认安全 dry-run，只有明确加 `--enable-actions` 才执行。

## 准备

G0 模拟已通过；如果接真实按钮则还需要 G1 实物通过。macOS Python 3.10+；真实 USB 连接需 `pyserial`。参考 [官方 pySerial 教程](https://pyserial.readthedocs.io/en/latest/shortintro.html)。

## 操作

1. 为串口依赖建立独立 Python 环境（不要污染 Homebrew/system Python）：

```bash
mkdir -p ~/.venvs ~/.config/agent-button-deck
python3 -m venv ~/.venvs/agent-button-deck
~/.venvs/agent-button-deck/bin/python -m pip install pyserial
cp source-data/agent-button-deck/host/mappings.example.json ~/.config/agent-button-deck/mappings.json
chmod 600 ~/.config/agent-button-deck/mappings.json
```

2. 编辑私有 `mappings.json`：K1 用 `{"type":"open_app","bundle_id":"com.apple.Notes"}`；K2 的 `open_url` 只接受 HTTPS；K3 `shortcut` 指向一个**你自己先在 Mac 快捷指令 App 创建并审阅**的名字。Shortcuts 的官方终端入口是 `shortcuts run "快捷指令名"`。
3. 用 `--list-ports` 看到真实串口后，替换示例值；**不要直接照抄下面的占位符**：

```bash
~/.venvs/agent-button-deck/bin/python source-data/agent-button-deck/host/agent_button_bridge.py --list-ports
~/.venvs/agent-button-deck/bin/python source-data/agent-button-deck/host/agent_button_bridge.py \
  --config ~/.config/agent-button-deck/mappings.json --port /dev/cu.<实际串口>
```

4. 先只观察 `[DRY RUN]`。确认每个按键对应的动作安全、可逆后，停止程序重启并**明确添加** `--enable-actions`。本地桥接仅允许 `open_app`、`open_url`、`shortcut`、`agent_event` 四类动作，不接受来自设备的任意命令或 shell 片段。

### K4：将按键投递到指定 Agent / Session 的边界

示例 K4：

```json
{"type":"agent_event","route_id":"research","endpoint":"http://127.0.0.1:8765/button"}
```

只有你自己部署了本机 adapter，才会向它 POST：

```json
{"source":"agent-button-deck","v":1,"event":"press","key":"K4","route_id":"research"}
```

adapter 负责把 `research` 映射到目标 Agent/Session，管理真实 API 权限、敏感操作审批、去重、回执和失败。**这个 PR 只有事件协议和本地调用，不包含可用于向 ChatGPT/Codex/飞书指定会话发送消息的实现，也不提供私人凭据**。没有 adapter 时 K4 失败并保留日志；打开会话网页只负责**打开**，不能被称为“发送消息”。

## 验收

- [ ] 修改 Mac 上的私有映射后，无需重刷 MCU，dry-run 显示新的对应动作。
- [ ] 默认模式无动作；`file:` 等不安全 URL、`shell` 类型、外网 Agent 端点配置全部拒绝。
- [ ] 在确认映射的前提下，真实 K1 能打开备忘录、K2 打开指定 HTTPS；K3 只有已经创建合法 Shortcuts 才验收。
- [ ] K4 仅当适配器有**合法真实回执**才可记为“路由到 Agent/会话已验证”。
- [ ] 不提交配置中的私人会话、密钥和 Mac 设备标识。

## 出问题怎么办

`No module named serial`：确认使用虚拟环境 Python 且安装的是 `pyserial`。串口 `Resource busy`：关闭 Arduino Serial Monitor，重插后再用 `--list-ports` 查找。K3 不工作：先在 Shortcuts App 手动执行，检查系统权限。K4 连接拒绝代表本机 adapter 没准备好；**不要偷偷改为公网 POST**。如出现不希望的动作，Ctrl-C 停止并撤销 `--enable-actions`。

**下一关**：[G3–G4 扩展与完整验收](/projects/agent-button-deck/04-extensions/)。
