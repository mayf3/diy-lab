# Maker Lab｜给 AI Agent 的工作约束

你在帮助维护一套**长期运行、可复刻的中文 DIY 教程和实测日志**，而不是仅仅生成文章。

## Agent-first DIY 双视图（2026-11）

面向外部新手的站点先看 [AI 帮我做](/guide/agent-first/)（源码 `content/guide/agent-first.md`）。**不要假设读者有 Bambu P1S、Apple silicon Mac、焊台、CAD 技能。**

- 核心原语 `D/O/A/V/R`：[DIY 原语说明](content/guide/diy-primitives.md)，执行约定 [AGENT_RUNBOOK.md](AGENT_RUNBOOK.md)。
- 在 `source-data/<slug>/workflow.json` 表示真实目标、设备/代工替代路径、Agent / 人 / 商家动作、证据、阻断依赖；`human-track.md` 与 `agent-track.md` 是**自动生成**的两种视图，禁止手改后造成漂移。
- 上游 GitHub、官方版本、CAD/PCB 文件和购物资料检索是**Agent 的工作**。具有工具权限时直接完成，不要把专业源代码调查转交零基础用户；无权限则如实标出缺口，最小化向用户索要文件/照片。
- 有风险的实物焊接、通电、产品打样、付款、不可逆烧录或现场验收仍须人/供应商完成；公开资料/模型分析**不能代替实物观察**。
- 更新工作流后运行 `python3 scripts/render_diy_ir.py`，随后 `python3 scripts/check.py`（会拒绝视图版本漂移）。

## DIY 视频生成：分镜就是有证据的派生视图

收到“为 DIY 加视频”的任务时，先读 [制作规范](content/guide/video-production.md)。优先用有权限的工具从已确认工作流、工程图与实际测试取得内容。视频片段分别标记 real physical / real screen / digital simulation / illustration；不得虚构用户动手画面或上游视频授权。Agent 应自行生成可重复渲染的分镜、素材清单、字幕和审查结果；人仍负责真实拍摄与发布授权。

G0 示例用 source-data/christmas-magic-tent/video/g0-storyboard.json + scripts/video_from_storyboard.py，生成的网站不依赖 Pillow/FFmpeg。原创短篇数字视频存 GitHub Release，大视频去视频平台，不把 MP4 加到 Git 历史。

## 必须遵守

1. **Issue-first**：说明正在解决的是哪一关、缺什么证据、会修改哪些文件，然后做尽量小的补丁。
2. **事实三分法**：`官方资料` / `计划或推测` / `实测观察`。没有图像/实验/订单/日志证据不允许写“已经成功”“验证通过”。
3. **来源与版本**：优先官方文档/立创/微雪原始链接；记录查看日期。软件和固件的“最新”必须当天检查，不要复制旧页面。
4. **新手可执行**：每章必须回答“要准备什么、先做哪个动作、应该看到什么、失败怎么办、完成后下一章做什么”。
5. **采购门禁**：识别型号、接口、尺寸、固件差异；有兼容不确定就标 `HOLD` 而不是凭概率推测可买。
6. **安全优先**：任何焊接/通电/儿童互动涉及的电气与机械风险应明确指出；不要诱导跳过官方保护或关闭安全校验。
7. **版权/隐私**：不未经许可复制官方 STEP/PCB/装配视频；不提交 API Key、订单、MAC 地址、孩子可识别信息、私人会话。
8. **维护最小复杂度**：本站只依赖 Python 与 Mistune，优先维护现有静态生成器，避免引入复杂服务、数据库或前端依赖。
9. **不碰生产**：不修改任何其他 GitHub 仓库、远程 Mac 生产代码或个人 Agent Workflow；只在当前 Maker Lab 路径工作。
10. **多会话共享工作区**：同一仓库可能有多个 Agent 会话并行工作。`git add` 必须逐个指定自己改动的文件，**禁止 `git add -A` / `git add .`**；提交前先看 `git status`，对不属于自己任务的未提交文件既不提交也不回退（包括 `git checkout` / `git restore`），发现他人改动时在日志中记录而不是处理。

## 新项目的最小文件

- `content/projects/<slug>/index.md`
- `content/projects/<slug>/01-workflow.md`
- `source-data/<slug>/bom.csv`
- `public/media/<slug>/`（自己的合法图片）
- `data/projects.json` 的一个项目条目
- `data/videos.json` 的一个拍摄计划条目（有计划才加）

用 `python3 scripts/new_project.py slug "标题"` 初始化。

## 完成标准（每次 PR）

- `python3 scripts/check.py` 通过；`python3 scripts/build.py` 可生成站点。
- 新教程有来源、版本与发布日期；有目标、操作、验收和排错。
- 所有重要外部材料带具体链接或“待核实”，没有伪造采购价格、结果或视频。
- 看过网站桌面和手机阅读布局，且更新了相关制作日志/状态。
- 如果更新工程数字（BOM、切片、成本），同时更新叙述和验证依据；不能只改结论。

## HachimoDock 当前必留疑点

`ESP32-P4 silicon v1/v3`、`2.8寸屏和 FFC 规格`、`PCB_V1.2 网表差异`、`BOX vs CPG135001D01 机械轴`。未有实测证据前，绝不可抹掉文档中的警示。

四个疑点结构化登记在 `source-data/hachimodock/blockers.csv`（状态 `open → asked → closed`），权威来源及查看日期登记在 `source-data/hachimodock/sources.csv`。`scripts/check.py` 强制：`closed` 必须附证据链接和核验日期；疑点未全关不得把项目标为 `verified`；来源/疑点超过 90 天未复核会输出警告。


## Remotion 视频输出（作者端）

有 Remotion 工作时：读取 `content/guide/remotion.md` 和 `video/remotion/README.md`，维护唯一真实分镜 `source-data/*/video/*.json`，用 `python3 scripts/prepare_remotion.py` 校验来源、复制授权媒体并生成 props，`npm ci` 后可运行 Studio / render。外部 DIY 读者不需要安装 Node。严禁将用 SVG/Blender 做的步骤示意伪称实物测量、购买、装配已成功。视频以 Release 等非 Git 历史方式发布，真实软件/实物操作需实录并标注来源。仓库已有其他会话 worktree 时不要修改其未提交文件。
