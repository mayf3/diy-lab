# Maker Lab 视频分镜模板

给每个 DIY 项目新增一个可自动生成的解释视频时：

1. 复制 examples 视频目录的 g0-storyboard.json，改项目、标题、源图片和证据类型。
2. 先保证真实画面素材存在；没有实物录像不能由 AI 编造为已测试。
3. 尽量一个镜头对应一个 Action 或 Verification，写清楚关键状态变化和要看的证据。
4. Agent 先运行 python3 scripts/video_from_storyboard.py --storyboard 路径 --check 验证存在性和证据声明。
5. 需要渲染时额外安装 Pillow、FFmpeg。建议视频生成到临时目录；GitHub 普通源代码库只保留脚本、分镜与合法缩略图。
6. 先人工看开头、中段、结尾；实际录屏和手部动作要视频对稿；字幕需校对专业型号和数值。
7. 发布到视频平台或 GitHub Release，然后登记 data/videos.json 并链接对应项目教程。

模板的 JSON schema 见 scripts/video_from_storyboard.py。示范源文件位于 source-data/christmas-magic-tent/video/g0-storyboard.json。文件没有声称提供真人录制或无条件支持任意素材来源。