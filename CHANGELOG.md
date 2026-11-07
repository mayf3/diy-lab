# 版本记录

## 视频工坊 v1（2026-11-07）

- 检索比较 Remotion、Motion Canvas、Blender Exploded Assembly Studio、OBS、Screenity、demo-machine、Auto-Editor、faster-whisper 的角色与许可。
- 发布一条圣诞互动帐篷 G0 的 53.54 秒数字模拟教学样片（真实已有 Blender G0 渲染图、8 镜头、字幕与证据清单），视频与字幕放 GitHub Release，非实物制作录像。
- 视频生产使用结构化 storyboard.json + 可选 Pillow/FFmpeg 生成器；加强网站 html5 播放、封面与关联图文链接，增加视频数据校验/回归测试。
- 不修改现有项目采购/验收结论；不新增静态站点的部署依赖。



## v0.3.0（Agent-first 双版本与 DIY 原语提案）— 2026-11-07

- 对公共新手教程取消“已有 Bambu P1S / Apple silicon Mac”的默认前提，增加自有打印、借用、代打印以及电脑平台与焊接资源分流。
- 将 GitHub、立创 EDA、BOM、CAD、官方发布资料的获取与核实明确委托有相应权限的 Agent；真实焊接、付款、通电、测量和实物验收仍需人或服务商完成。
- 提出 DOAVR 五原语（D/O/A/V/R），以 `source-data/hachimodock/workflow.json` 为单一流程事实源，自动生成 `human-track.md` 与 `agent-track.md` 两种阅读视图。
- 新项目脚本自动创建原语模板与双视图；内容检查拒绝视图漂移和无证据的 observed 状态，增加回归测试（含新项目从零构建）。
- 保留 HachimoDock 原有 13 关深入教程、BOM 与历史证据边界；不把未采购/未实物测试的项目标为完成。

关联 [Issue #4](https://github.com/mayf3/diy-lab/issues/4)。


## v0.2.1 — 2026-11-06

- 本机常驻预览服务：`build.py` 在检测到镜像目录 `~/Library/Application Support/MakerLabSite/` 时自动同步 `dist/`；LaunchAgent（`com.mayf3.makerlab.site`）在 `http://127.0.0.1:8123/` 提供只绑定 127.0.0.1 的站点服务。镜像目录置于 TCC 非保护区，规避 launchd 进程无 `~/Documents` 访问权限的问题；README 增加说明。

## v0.2.0 — 2026-11-06

- 圣诞互动帐篷 G0 数字模拟完成：Blender 参数化脚本（`--variant A/B` 一键重建）+ 18 项几何检查 0 FAIL；门洞×屋顶净空 A 10.0cm / B 20.9cm；站立净空条带（30/43.6cm）与 3.0×3.5m 小区域动线压力测试（门扇与帐篷角仅 5cm）列为采购前复核项。
- 新增 G0 评审教程页（目标/验收/排错 + 可勾选关卡）、17 张渲染图（每张 ≤3MiB 门禁内）、两个 .blend 工程、尺寸 CSV 与检查 JSON（`source-data/christmas-magic-tent/g0/`、`public/media/christmas-magic-tent/g0/`）。
- 项目页勾选前两关并标注"数字模拟证据，非实物验证"；结论边界：几何检查通过 ≠ 实物安全验证，仍不采购，下一步回填真实商品尺寸与真实房间数据重跑。

## v0.1.2 — 2026-11-06

- 新增 `source-data/hachimodock/blockers.csv`：把四个必留疑点（silicon 版次、屏幕 FFC、PCB 网表、机械轴封装）结构化为 `open → asked → closed` 登记行；`check.py` 强制 `closed` 必须附证据来源与核验日期，未全关不得标记项目为 `verified`。
- 新增 `source-data/hachimodock/sources.csv`：权威来源登记（精确网址、版本标识、查看日期）；`check.py` 在超过 90 天未复核时输出非失败警告。
- `build.py` 把两个新登记表随 BOM 一起复制到 `/downloads/`；采购执行单与第 2 关挂链说明。

## v0.1.0 — 2026-11-06

- 建立 Maker Lab 中文静态教程站：适配桌面/手机、离线预览、搜索、可勾选进度和项目目录。
- 加入 HachimoDock 从资料核实到出片复盘的 13 关教程、BOM CSV、付款前门禁、真实状态标注。
- 为两项已完成的万圣节 DIY 建立待整理档案；为圣诞互动帐篷建立规划档案。
- 加入视频工坊，支持 B 站成片链接及点击后加载播放器，不假设未拍素材已存在。
- 加入 `new_project.py`、断链/BOM/质量验证脚本、GitHub Actions Pages 部署。
- 当前所有 HachimoDock 结构件/电路板/屏幕兼容和实机验收尚未由用户执行；不可当作实体测试通过。

## v0.1.1 — 2026-11-06

- 创建 `mayf3/diy-lab` 仓库并完成 GitHub Pages 首次部署、访问检查；设置 HachimoDock 采购门禁和结构模拟 GitHub Issues。
- 万圣节两项已完成项目补入确定的历史设计参数；继续区分数字模型计划、实际完成和待补的照片/花费。
- 圣诞互动帐篷补入具体尺寸、四层目标与不采购先模拟任务。
- 补充 HachimoDock 采购执行单，优先核对 ESP32-P4 silicon 版次、DSI 排线、机械轴与 PCB。

## Remotion DIY 视频底座（2026-11-07）

- 安装 Remotion 4.0.541 的隔离作者端工程，复用原有圣诞帐篷 G0 分镜并增加 HachimoDock 采购前示意分镜。
- 提供动态 React SVG 零件关系、转场/字幕卡、Studio 预览与完整 MP4 渲染流程；所有镜头绑定 Action + Evidence。
- 新增 props/图片复制脚本与有来源的 SRT/manifest 导出，测试 source data 防越界与数字/示意/实物的证据区别。
- Remotion 按自己的授权条款使用，不随网页向读者加载；视频成片链接与实物验收状态分开管理。
