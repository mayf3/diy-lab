# Maker Lab Remotion 视频引擎

Remotion 4.0.541，作为**可选作者工具**。普通读者访问 GitHub Pages 不需要 Node、Remotion 或 3D 打印机。

## 使用

在仓库根目录运行：

```bash
python3 scripts/prepare_remotion.py
cd video/remotion
npm ci
npm run studio
```

Remotion Studio 预览 `ChristmasTentG0` 和 `HachimoPrepurchase`。

生成：

```bash
npx remotion render src/index.tsx ChristmasTentG0 /tmp/christmas-tent-remotion.mp4 --concurrency=3
npx remotion render src/index.tsx HachimoPrepurchase /tmp/hachimo-prepurchase-remotion.mp4 --concurrency=3
```

以后新增项目无需修改 React 入口，只要把分镜 JSON 放进 `source-data/<project>/video/`，在 `video/remotion/catalog.json` 添加唯一 `id` 和源文件路径，运行准备脚本即可生成一个新 Composition。

资料源是 `source-data/christmas-magic-tent/video/g0-storyboard.json` 和 `source-data/hachimodock/video/remotion-prepurchase.json`，只改源分镜，不改自动生成的 `props/`。运行 `prepare_remotion.py` 重建视频 Props 和合法原图到 `public/images/`。

标注：帐篷示例为数字几何模拟；HachimoDock 示例仅有抽象示意与来源核查，并没有实际开箱、焊接、接线、烧录、实物验收。**不能声称已经完成硬件制作。**

出版视频到 GitHub Release 或 B 站；不要把原视频塞进 Git 历史。检查 [Remotion 许可证](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)：个人与符合条件的小团队可免费，其他组织可能需 Company License。

## 圣诞小屋分步操作动画

新 Composition：`ChristmasHandsOnLesson1`，读取同一份 `assets/christmas-steps/course.generated.mjs` 和 `scene.mjs`，动画不冒充实物。

```bash
python3 scripts/build_christmas_hands_on.py --check
python3 scripts/prepare_remotion.py
cd video/remotion
npx remotion compositions src/index.tsx
# 需要完整高清制作时：
npx remotion render src/index.tsx ChristmasHandsOnLesson1 /tmp/christmas-lesson1.mp4 --concurrency=1
```

仓库同时提供 `scripts/render_christmas_lesson_cdp.py` 轻量录制版本，按本地站点、Chrome CDP 9222、Python `websockets` 与 FFmpeg 使用；它复用同一 SVG 图形和动作数据，输出 8fps 40 秒快览。完整互动教程不依赖这些作者工具。
