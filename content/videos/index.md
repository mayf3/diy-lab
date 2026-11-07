# 视频工坊

这里汇集每个 DIY 项目的真实操作录像、3D 数字模拟视频、B 站成片链接和分镜记录。目前已发布**两条 Remotion 动画教程**（HachimoDock 采购前结构示意、圣诞帐篷 G0 数字模拟），以及一条早期 G0 技术样片；HachimoDock 等项目仍未有实物制作录像，不会把数字示意或第三方参考视频冒充自己的实拍。

[HachimoDock Remotion 采购前动画](/projects/hachimodock/video-prepurchase/) · [圣诞帐篷数字模拟](/projects/christmas-magic-tent/g0-review/) · [Remotion 制作步骤](/guide/remotion/) · [真实 DIY 待拍镜头](/projects/hachimodock/12-video/)

## 为什么把视频也当作教程的一部分？

文字适合精确的尺寸、购物型号和排错；视频擅长告诉新手手怎么动、排线朝哪边、焊点是否合适。两者应该互相链接：**视频的每一个关键动作，都能回到对应的文字章节和验收标准**。

## 视频目录

## 如何制作和发布下一条视频

视频工坊现在有两种成片来源：数字模拟（例如 G0）与未来的实拍教程。它们可以用同一套分镜、字幕和网站入口，但必须保留**来源证据**。具体推荐开源工具、Agent 分工、质量门禁和 MP4 自动生成方式，请看[视频制作完整指南](/guide/video-production/)。

### 从自己拍摄的真实操作开始

1. 根据项目的 [拍摄模板](/projects/hachimodock/12-video/) 拍摄真实操作。
2. 剪辑完成后发布到 B 站/YouTube，不上传大文件到 Git 历史。
3. 在 data/videos.json 中登记：设为 published，填实际视频链接、证据类型、图文关卡与字幕链接。B 站用 embed=bilibili；本站自制的短篇数字模拟样片可以由 Agent 按 GitHub Release 受控 MP4 URL 配置 embed=html5。
4. 运行 `python3 scripts/check.py` 和 `python3 scripts/build.py`。随后网页会出现“观看视频”入口；发布前不会出现假的播放器。
5. 在视频描述中附上对应教程版本，避免后续修改让观众跟错版。

## 著作权和隐私

不能在无许可情况下转载 HachimoDock 官方 `.mp4`；发布自己的视频也要检查孩子隐私、订单个人信息、API Key 和私人 Agent Session 内容。


**Remotion 视频制作已正式纳入流程：**[Remotion 使用说明](/guide/remotion/)，目前可以把已保存的 DIY 工程分镜做成有动画与字幕的教程。具体哪些视频已实际发布、哪些仍待拍摄，以本页目录为准。
