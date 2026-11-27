# 本机硬件工作台

这个入口把 Lab 项目的产品目标、当前进度、需要本人处理的事项、资料和备注放在一起。页面由 `web/workbench.json` 提供项目事实；轻量本机服务负责查连接、保存备注和打开已登记的应用/项目文件夹。服务只依赖 Python 标准库。

## 启动和检查

在仓库根目录执行：

```bash
python3 workbench/serve.py --check
python3 workbench/serve.py
```

打开 <http://127.0.0.1:8135/>。检查成功表示页面配置能读到；状态中的 `app_installed`、`cli_available`、`bridge` 和 `editor_round_trip` 分别描述实际环境，不能互相替代。尚未激活不阻止工作台启动。既有教程站点的 8123 端口不受影响。

参数：

```text
--port 8135
--host 127.0.0.1
--state-file /absolute/path/to/workbench-state.json
--check
```

`--host` 只接受回环 IP 或 `localhost`，不提供外网/局域网访问。`--check` 运行一次有超时限制的环境检查后退出，不启动网页服务。

在 Mac 上安装桌面入口并启用本人登录后自动启动工作台：

```bash
python3 workbench/install_macos.py
```

安装脚本会新增用户 LaunchAgent，并在桌面创建 `.webloc` 网页快捷入口。登录 Mac 后工作台服务自动启动，双击桌面入口即可打开页面。既有教程站点继续使用 8123 端口。

## 数据和实际动作

- `web/workbench.json`：项目、页面内容及文档 allowlist。项目 `workspace`、文档 `path` 均为仓库相对路径。项目文件夹必须已存在，路径和符号链接不能越出仓库。
- `docs/eda/environment-status.json`：已有安装及验收记录。服务检查当前电脑上的应用包、真实可执行文件和技能文件，并在启动及状态刷新时实际调用已记录支持的 `doctor`，每次最多等待 5 秒。
- `~/Documents/DIY/eda-toolchain/workbench-state.json`：本人的备注，采用原子替换写入，不进入仓库。可通过 `--state-file` 明确指定测试位置。损坏或不可写时返回错误并保留旧文件，不返回虚假的“保存成功”。

服务从应用包的 `Info.plist` 查找可执行文件，不把安装路径拼成猜测的二进制名称。`doctor` 已连接只说明本机桥接有回应；它不会消除“待官方激活”，不会创建编辑器 session，也不会把工程或硬件标为验证通过。编辑器往返只在已有明确验收记录和当前有效连接同时存在时显示 `passed`。

“打开 EDA”仅请求 macOS 打开已登记的应用；“打开项目”仅打开已登记且存在的项目目录。返回成功表示系统接受打开请求，不表示应用完成激活或工程已执行。Linux 预览环境对这两个动作返回明确的不支持结果。

工作台不读取激活文件，不保存账号凭证，不接受任意命令、任意文件路径或后台 Agent 任务，不自动打板、下单、付款或烧录。

## API 合同

| 请求 | 成功结果 |
|---|---|
| `GET /api/status` | `{mode, checked_at, app_installed, cli_available, skills, bridge, activation, editor_round_trip}` |
| `GET /api/notes` | `{notes: {project_id: {text, updated_at}}}` |
| `POST /api/notes`，`{project_id,text}` | 返回保存后从磁盘读回的 `{notes: ...}` |
| `POST /api/actions`，`{action:"open_eda"}` | `{ok:true,action,detail}` |
| `POST /api/actions`，`{action:"open_project",project_id}` | `{ok:true,action,detail}` |
| `GET /documents/<id>` | 仅返回 allowlist 内的文件；文本按纯文本显示，其他文件下载 |

所有 POST 要求：

```text
Origin: http://127.0.0.1:8135
Content-Type: application/json
X-Workbench-Request: 1
```

浏览器同源 `fetch` 自动提供 Origin。Host 和 Origin 必须对应实际本机端口；不提供 CORS。备注最多 8000 个字符，请求体最多 64 KiB。非成功响应统一使用 `{error:{code,message}}`；前端应保留尚未保存的输入并展示错误。

`bridge.state` 为 `connected`、`disconnected`、`unavailable`、`error` 或 `timeout`；`activation.state` 为 `pending`、`unverified` 或 `verified`（verified 需要客户端接受官方激活与编辑器读写往返验收两类证据同时存在）；`editor_round_trip` 为 `pending` 或 `passed`——`passed` 要求历史验收记录（含 `editor_round_trip_passed_at`）、激活已验证且当前桥接在线三者同时成立，任一不成立时实时状态降级为 `pending`，历史通过时间保留在 `editor_round_trip_evidence_at`。状态响应额外包含 `ready`（上述全部条件与安装、命令行同时成立）与 `ready_blockers`（具体待处理项列表），不返回设备路径或许可证内容。

静态文件仅从 `web/` 提供，不列目录，拒绝路径穿越和指向根目录外的符号链接。页面脚本应放在独立本地 JS 文件，内容安全策略不允许内联脚本。文档接口额外使用纯文本/下载与沙箱响应头。

## 针对实际风险的测试

```bash
python3 -m unittest discover -s workbench -p 'test_server.py' -v
```

测试通过真实回环 HTTP 请求验证 Host/Origin、防跨站操作、路径/符号链接边界、备注并发与原子保存、允许的打开动作和失败结果。环境测试运行临时的可执行 `doctor` 替身，验证服务确实探测当前结果、保留未激活状态并限制超时；它不是 Mac EDA 实机验收。Mac 上的真实连通和页面验收应另外记录。
