# DIY 视频工坊｜用 Agent 把制作流程变成真正有用的教学视频

> **2026-11-07 研究与实作。** 站点教程面向没有专业工具的新手。Agent 优先完成资料查证、分镜、可生成的模拟画面、剪辑和字幕；人负责真实拍摄、实物操作、采购与发布授权。**实物录像、电脑录屏、数字模拟、插画必须清楚区分。**

[第一条模拟教学样片](/videos/) · [对应 Blender G0 图文教程](/projects/christmas-magic-tent/g0-review/) · [DIY 原语](/guide/diy-primitives/)

## 一条视频解决一个真实制作问题

例如“买帐篷前怎样发现门洞尺寸冲突”比泛泛的“完整制作全过程”更适合第一次录制。片头 3–6 秒说明痛点，每个镜头给出一个可观察的动作，结尾告诉新手下一步怎样自己验证。

视频镜头是 DOAVR 的**派生视图**，不需要再造一套庞大的视频本体：

| DIY 原语 | 视频中怎么呈现 | 防止误导 |
| --- | --- | --- |
| D：制作目标、受众 | 开场问题、看完能做到的事 | 不能为了悬念夸大实测成果 |
| O：物件、材料、资源 | 真实材料、尺寸图、3D 模型、工具图片 | 图片标明真实/模拟/示意来源 |
| A：行动与执行者 | 人实际动手的步骤、Agent 的软件分析或工具操作 | 动画和计算不能假装焊接已成功 |
| V：验证与证据 | 尺寸、日志、检查截图、失败和修复对照 | 数字通过 ≠ 实物通过 |
| R：依赖与替代 | “型号不符暂停”“没有打印机则代打印” | 不引导跳过付费/安全门禁 |

## 搜到的 GitHub 项目：每种工作只选一款

| 位置 | 开源工具 | 能做什么 | 许可 / 边界 |
| --- | --- | --- | --- |
| 视频模板主力 | [Remotion](https://github.com/remotion-dev/remotion) | React 做标题、过场、动画、字幕、参数化短视频 | **专门的许可条款**，个人和部分小团队免费，其他企业需检查 [官方许可证](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) |
| 原理与步骤动画 | [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | 用 TypeScript 做动态线框、操作流程与语音同步 | MIT；不是视频剪辑软件 |
| 3D 装配爆炸图 | [Blender Exploded Assembly Studio](https://github.com/ehsun-sh/blender-exploded-assembly-studio) | 从正确组装的零件模型生成拆解/组装动画，尤其适合 PCB 与机壳 | GPL-2.0-or-later；不能自动证明零件真正装得下 |
| 录真实电脑界面 | [OBS Studio](https://github.com/obsproject/obs-studio) | Blender、切片器、Wokwi 与烧录工具的真实屏幕录制 | GPLv2+；需要录制设置 |
| 浏览器操作教程 | [Screenity](https://github.com/D0x22/screenity) | 录网页、箭头、高亮鼠标、剪掉多余片段 | 当前版本 GPLv3；不等于真实实体演示 |
| 录制可重播的网页演示 | [demo-machine](https://github.com/45ck/demo-machine) | YAML + Playwright：按步骤演示网站界面与操作，输出 MP4 | MIT；小而新的项目，应先验证再作为核心依赖 |
| 真人录像初剪 | [Auto-Editor](https://github.com/WyattBlue/auto-editor) | 自动根据声音停顿裁减冗余片段 | Unlicense；不要自动删掉有教学意义的操作停顿 |
| 配音字幕校对 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 本地转写口播，生成带时间戳的文字草稿 | MIT；引脚名称与单位仍需核对 |

**Maker Lab 视频工坊已采用 Remotion 作为标准的新视频制作底座。** [Remotion 视频工程与命令](/guide/remotion/) 可直接在 Studio 中预览、渲染，使用项目事实源生成视频；过去的 Pillow + FFmpeg 样片作为轻量历史实现保留。**浏览网站的普通读者仍无需 Node 或 Remotion。**

## Agent 到成片的七步 SOP

1. **定位动作**：读取项目当前 Agent / Human 工作流和已提交的实测/模拟记录，选最值得教会新手的一关。
2. **核对事实**：确认产品型号、尺寸、代码、视频时间点；标记“官方/数字模拟/真实物理观察/待测”。
3. **写结构化分镜**：每镜头写明时长、文案、素材路径、action_ref（动作锚点）、evidence_ref（实际存在的证据文件）、证据类别、字幕/口播稿。
4. **做数字素材**：根据已经存在的 Blender、切片器或电路仿真结果生成说明画面；别把画出来的“成功组装”当成真实验收。
5. **列真实拍摄缺口**：没有实物就留下“需拍摄”任务，给人具体机位、手部动作、开始/结束状态；不要生成假实拍。
6. **剪辑与 QA**：让 Agent 出草片、字幕、封面、事实核查报告。检查每个难点是否能看到方向和结果，观看时长是否足够新手跟着做。
7. **发布与回链**：大视频发 B 站/YouTube，短数字示例可放 GitHub Release；站点关联对应图文关卡、版本、素材来源和实际验收状态。

有合适工具权限的 Agent 应自行查看 GitHub 和项目文件，不要求初学者研究源代码。人仍需亲自拍摄真实手部操作、提供安全实测证据、批准付费和确认公开视频的隐私/版权。

## 已做出的样片：圣诞互动帐篷 G0 尺寸模拟

本次真正生成了一条**53.54 秒、1280×720、24fps** 的历史无配音字幕卡片视频（现已有 [Remotion 升级版](/guide/remotion/)），使用 Maker Lab 自有的 Blender G0 渲染图；展示参数 A/B 对比、门顶净空、儿童站立空间、假想房间动线与电子布局预留。

**明确说明：这是数字模拟教学样片，不是实物制作、商品验收或儿童安全认证。** 口播文案随分镜保存，尚未录制或声称有人配音；可另下 SRT 文稿用于以后补真实配音。

[打开可播放的视频文件](https://github.com/mayf3/diy-lab/releases/download/makerlab-video-g0-20261107/makerlab-g0-digital-tutorial.mp4) · [下载 SRT](https://github.com/mayf3/diy-lab/releases/download/makerlab-video-g0-20261107/makerlab-g0-digital-tutorial.srt) · [机器可读分镜](https://github.com/mayf3/diy-lab/blob/main/source-data/christmas-magic-tent/video/g0-storyboard.json) · [对应图文教学](/projects/christmas-magic-tent/g0-review/)

### 复现同一视频

使用 Python 3.10+、Pillow 和 FFmpeg（用于制作视频，与网页部署无关）。Agent 有对应工具时直接执行：

~~~bash
# 在 diy-lab 仓库根目录
python3 scripts/video_from_storyboard.py --check

# 只为本机视频制作装 Pillow；还需系统已安装 FFmpeg
python3 -m pip install Pillow
python3 scripts/video_from_storyboard.py \
  --output /tmp/makerlab-g0-digital-tutorial.mp4
~~~

生成 MP4、SRT、渲染证据 JSON，以及有来源标注的封面。修改 source-data/christmas-magic-tent/video/g0-storyboard.json 可重排镜头；素材文件必须存在，脚本拒绝读取工作区外的不受控路径。视频是 GitHub Release 附件，**没有把 MP4 放进 Git 历史**。

## HachimoDock 下一条视频应该是什么？

优先做“下单前看清主控芯片版次、屏幕与 FFC 接口”的视频：Agent 通过官方文件/零件尺寸图整理准确的示意画面；只有拿到实物后，才拍摄屏幕排线真实插拔、焊接、首次烧录、亮屏和故障排查。可以把各段真实录像与 Blender 爆炸图放在一起，但二者证据等级绝不能混同。

每一实物步骤都按**操作前 → 手部动作 → 检查结果**拍三个镜头；关键方向或极性用特写，失败时留下清楚的返工对照。没有打印机的读者还需要“代打印路线”，不能把 P1S 当所有人的必备工具。

## 发布前质量门禁

- [ ] 核对每个尺寸、型号和演示主张的来源，以及证据属于模拟还是实物。
- [ ] 片头和视频描述标注“数字模拟”时，不出现伪造的真人安装或误导式成功口吻。
- [ ] 每个核心动作包含动词、可见效果、失败时的停止条件；移动端能看清数字、方向与字幕。
- [ ] 已查看真实输出文件的开头、关键中段、结尾，而不仅是生成命令返回成功。
- [ ] 任何原作者 STEP/PCB/视频、版权音乐和生成声线都应有对应授权，不从“能下载”推断允许再发布。
- [ ] 不泄露订单地址、私密工作流、API Key、孩子身份、学校或其他个人信息。
- [ ] 视频上线后，加入图文步骤和实际测试来源，记录版本与日期；**观众进度勾选不等于实物通过**。

视频不是另外一套真相账本：工作流和 G0/BOM/实测日志仍是事实来源，视频只引用它们。
