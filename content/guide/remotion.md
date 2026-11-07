# Remotion 视频工坊｜代码生成 DIY 教程

> 已接入 Maker Lab 的 DOAVR 原语与有来源的步骤分镜。**网站面向公众，不需要安装 Remotion；只有作者或 Agent 制作新视频时需要 Node。**

## 选用 Remotion 的原因

视频与教程、BOM、来源登记表一起维护，可重复渲染，不必人工逐段拖剪。相比原来的 Pillow+FFmpeg 卡片样片，Remotion 用 React 组件统一尺寸、配色、场景动画、字幕与示意图，更便于以后扩展 Blender 装配爆炸图、真实录屏片段和逐步操作动画。

目前有两个 Composition：`ChristmasTentG0` 与 `HachimoPrepurchase`。前者沿用已经存在的 G0 Blender 模拟图，后者使用项目原创 SVG 结构示意，**不是官方精确电路图、不是已安装成功的实拍**。

## 快速制作

```bash
# 仓库根目录（Python 3.10+）
python3 scripts/prepare_remotion.py --check
python3 scripts/prepare_remotion.py
cd video/remotion
npm ci
npm run studio
# 打开 Remotion Studio 预览所有构图
```

macOS 可以直接指定已安装 Chrome。输出不进入 Git 历史：

```bash
npx remotion render src/index.tsx HachimoPrepurchase /tmp/hachimo-prepurchase.mp4 \
  --concurrency=4 --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

npx remotion render src/index.tsx ChristmasTentG0 /tmp/christmas-tent-g0.mp4 \
  --concurrency=4 --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd ../..
python3 scripts/remotion_captions.py HachimoPrepurchase /tmp/hachimo-prepurchase.mp4
python3 scripts/remotion_captions.py ChristmasTentG0 /tmp/christmas-tent-g0.mp4
```

生成 MP4、SRT 和包含时间、源文件、证据等级、SHA-256 的 manifest，影片版本写入 `data/videos.json` 后发布。主要项目素材仍保存在源数据文件里，不另建并行的真相仓库。

## 新增一个 DIY 视频：不需要改 React 组件

在 [catalog.json](https://github.com/mayf3/diy-lab/blob/main/video/remotion/catalog.json) 登记新 Composition ID 和 storyboard 路径，基于现有分镜复制一个 JSON，并填入真实可验证的 action_ref 与 evidence_ref。运行 `python3 scripts/prepare_remotion.py`，Remotion Studio 会自动出现新视频。绘图样式、时长计算、字幕卡、证据标识都用同一套组件，只有复杂的全新图例才需要扩展 React。

## 只修改一处素材来源

- 圣诞帐篷：`source-data/christmas-magic-tent/video/g0-storyboard.json`，所指原图均已由项目 Blender G0 生成
- 哈基米机：`source-data/hachimodock/video/remotion-prepurchase.json`，每镜头关联 DOAVR A02/A03/A04/A06 与 `blockers.csv`
- 通用画面：`video/remotion/src/Tutorial.tsx`
- Remotion 入口：`video/remotion/src/Root.tsx`
- 准备资源和验证：`scripts/prepare_remotion.py`
- 字幕和证据清单：`scripts/remotion_captions.py`

任何新增镜头要有 `action_ref`、`evidence_ref`，模拟镜头必须有明确标识。如果本项目没有实物或授权图片，不得从图片搜索结果取一张冒充实际测试。

## 已发布的两条 Remotion 成片

- [HachimoDock 采购前检查（53 秒）](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-hachimo-20261107/hachimo-prepurchase-remotion-v1.mp4)，基于抽象工程示意，不能作为接线和装配依据。附 [SRT](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-hachimo-20261107/hachimo-prepurchase-remotion-v1.srt)。
- [圣诞帐篷 G0 结构模拟（56 秒）](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-g0-20261107/christmas-g0-remotion-v1.mp4)，复用既有 Blender 数字模拟图，不代表真实商品或儿童使用安全。附 [SRT](https://github.com/mayf3/diy-lab/releases/download/makerlab-remotion-g0-20261107/christmas-g0-remotion-v1.srt)。
- 以上两条可以在 [Maker Lab 视频工坊](/videos/) 浏览器直接观看，或查看各自 GitHub Release 中的证据 manifest。

## 怎样扩充成真正的零基础实物教程

按工程步骤拆分成 5–15 秒可复用短片，记录 **操作前 / 操作手法 / 操作后验收**。需要手部实拍，先按具体机位拍摄。Remotion 使用静态图片、真实视频片段或 Blender 渲染图进行编排；**不能用生成式图片假装已经完成电子实验**。配音可接用户提供或明确可使用的语音；本期样片不添加来源不明的音乐。

## 许可与运营

Remotion 使用不同于 MIT 的授权。参见 <https://www.remotion.dev/docs/license/pricing> 与 <https://github.com/remotion-dev/remotion/blob/main/LICENSE.md>。个人、符合条件的最多 3 人团队和非营利组织通常可以按 Free License 使用。**较大企业、收费视频自动化服务的用法必须先核对商业许可**。这里安装依赖仅用于作者端视频制作，不会让 GitHub Pages 的读者运行 Remotion 代码。

官方参考：<https://www.remotion.dev/docs/composition>、<https://www.remotion.dev/docs/render>、<https://www.remotion.dev/docs/options/browser-executable>。
