# 圣诞帐篷 G0 视频样片｜工程说明

- 分镜唯一来源：g0-storyboard.json。每个镜头都有 action_ref 与 evidence_ref，分别指向 G0 教学动作和既有源码/检查数据，不另建第二套验收事实。
- 原始图像：public/media/christmas-magic-tent/g0/ 的 G0 Blender 数字渲染，现有自制图，不是用户实物照
- 视频证据：53.54 秒、1280×720、24fps、H.264，2026-11-07 本地渲染；无音轨，提供独立 SRT 文稿
- 视频成品：GitHub Release makerlab-video-g0-20261107 下的 makerlab-g0-digital-tutorial.mp4、同名 .srt 与 .manifest.json
- 关联图文：content/projects/christmas-magic-tent/g0-review.md
- 渲染命令：在仓库根目录运行 python3 scripts/video_from_storyboard.py --check，再运行 python3 scripts/video_from_storyboard.py --output /tmp/makerlab-g0-digital-tutorial.mp4
- 构建依赖：本地制作需要 Pillow + FFmpeg，不属于静态网站部署依赖
- 注意：任何画面中的尺寸为 G0 候选模型的几何推导；**不代表已采购商品、实物、人体工学与电气安全得到验证**。本片与后续真实采购决策时间线不是同一个版本的实测。

修改视频前：先更新 G0 源数据和图文论证，再按脚本重新生成画面，不要只在视频上直接改数字。加配音或实拍需要新版本与明确音视频素材授权。