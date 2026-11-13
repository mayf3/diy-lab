---
name: mayf3-visual-style
description: Apply the shared Learn seaside visual style to Mayf3 websites and workbenches. Use for backgrounds, colors, typography, cards, controls and cross-project visual consistency; preserve each product's layout and behavior.
---

# Mayf3 统一视觉

以 Learn 的青雾海景与纸面排版为基准。业务代码继续由各项目维护，主题来源是 `mayf3-visual-system` 的固定版本发布包。

## 接入与维护

- 先读消费项目的 `visual-system.lock.json`，找到固定版本的 `manifest.json`、`seaside.css` 与背景图。核对文件哈希，不用另一个网站的在线 CSS，也不引用本机其他仓库的绝对路径。
- 新接入可运行共享仓库的 `tools/sync-consumer.py --project-root <项目> --target <项目内目录> --version 0.1.0`。该命令只同步视觉文件并写锁文件，不改业务入口。用 `--check` 核验，更新版本由项目显式选择。
- 网页加载 `seaside.css`，给 body 加 `mf-theme-seaside`。现有变量映射到 `--mf-*`，局部适配只处理产品现有控件与布局。
- 静态服务不允许增加资源路由时，把同版本 `seaside.inline.css` 原样嵌入既有 CSS；它由同一源文件生成并内置同一张图。用清楚的起止注释包住共享块，不手改共享块内部。
- 通用改进在共享仓库 `src/tokens.json`、`src/foundation.css` 修改，发布新版本，再分别升级各项目。已发布版本不原地改写。

## 必须保持的视觉

- 海景图由发布包提供；桌面青雾遮罩 .60→.75，小屏 .72→.85。阅读区用近似不透明纸面，不让背景干扰正文和控制台读数。
- 墨色 `#27302e`；纸色 `#f0f4f4`；苔绿 `#64735a`；赭色 `#bf704e`。优先读 `--mf-*`，不用一套独立色值重新实现主题。
- 标题用衬线，正文用中文无衬线，编号/时间/元数据用等宽字体。正文维持可读字号与行距。
- 卡片与控件采用 1px 细边线、2px 小圆角、克制留白，不增加浮夸阴影、发光、悬浮动画或全屏磨砂。
- 工具页保留自己的密度、导航、表格和编辑区。共享的是颜色与视觉语言，不要求所有产品采用同一页面布局。
- 成功、警告、错误、禁用、选中态及图表系列需要继续可区分。波形、字幕高亮、代码和图表根据浅背景适配，不能只改 body。
- 交互演示与视频画面中的语义颜色属于产品内容，不用主题自动覆盖。网站主题不重画第三方动画素材。

## 验证

至少看一个桌面和一个 390px 页面，检查背景加载、正文对比、控件状态、窄屏溢出和键盘焦点。地图同时看节点详情，Learn 同时看课程实验，工作台看编辑区，DIY Lab 看项目详情。

执行消费项目已有的相关构建/检查。区分源码接入、本地预览和线上部署；未经实际发布，不声称线上已更新。
