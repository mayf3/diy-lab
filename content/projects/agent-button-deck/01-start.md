# G0｜先用模拟按键控制电脑：不用购买任何设备

## 目标

验证“JSON 按键事件 → 配置映射 → 电脑动作”的链路。默认只预览要做的事，不执行 App、网页、Shortcut 或 Agent 请求。

## 准备

Mac/Linux/Windows 任意具备 Python 3.10+ 的电脑和 `diy-lab` 仓库。本阶段无需 pyserial、开发板、焊台、3D 打印机或 API Key。

## 操作

1. 在仓库根目录查看 `source-data/agent-button-deck/host/mappings.example.json`，确认 K1、K2、K3、K4 的不同动作。
2. 运行以下离线模拟；预期打印四条 `[DRY RUN]`：

```bash
python3 source-data/agent-button-deck/host/agent_button_bridge.py \
  --config source-data/agent-button-deck/host/mappings.example.json --stdin <<'EVENTS'
{"v":1,"event":"press","key":"K1"}
{"v":1,"event":"press","key":"K2"}
{"v":1,"event":"press","key":"K3"}
{"v":1,"event":"press","key":"K4"}
EVENTS
```

3. 再输入 `{"v":1,"event":"press","key":"K999"}` 应拒绝；不允许未知键或任意 `shell` 动作。
4. 你要编辑的真实映射以后放在 `~/.config/agent-button-deck/mappings.json`，不提交仓库；此阶段**不要**加 `--enable-actions`。

## 验收

- [ ] 四个事件分别映射到四个声明的动作，均只有 dry-run。
- [ ] 没有启动 App、打开 URL、运行 Shortcut 或发 POST。
- [ ] `K999` 被拒绝，未映射动作不会自动执行。
- [ ] 明确“打开一个会话网页”与“向会话发消息”是不同的验收项。

## 出问题怎么办

如果命令找不到文件，请先 `cd` 到有 `data/projects.json` 的仓库根目录。若提示 Python 版本过旧，改用 Python 3.10+，不要修改全局依赖。输入必须是一行一个 JSON 对象；看到 `[DRY RUN]` 才是正确结果。

**下一关**：[G1 硬件接线](/projects/agent-button-deck/02-hardware/)。
