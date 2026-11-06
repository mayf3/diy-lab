# Maker Lab｜我的 AI DIY 实验室

> 一个长期可维护的中文 DIY 教程网站。让新手按步骤复刻作品，把材料、购物、结构仿真、制作、验收、视频与失败记录留在同一个 GitHub 仓库。

**第一个完整案例**：[HachimoDock 哈基米机](content/projects/hachimodock/index.md)（2026-11-06，**准备中、未做实物验证**）。另外补录 2026 万圣节服装/门饰的制作参数与数字设计证据边界，以及圣诞互动帐篷的参数化模拟计划；历史项目的最终文件与实物验收证据尚待回填。

**2026-11-06 更新**：已由用户 GitHub 账户创建公开仓库 <https://github.com/mayf3/diy-lab>。网站已经通过 GitHub Pages 自动部署，并验证可访问：<https://mayf3.github.io/diy-lab/>。

## 第 1 步：在自己的 Mac 上预览网站

1. 下载并解压整个 `diy-lab-repo.zip`，文件夹建议放在 `~/Documents/DIY/diy-lab/`。
2. 直接双击 `dist/index.html` 就能打开**已生成的离线网站**（压缩包附带一次静态构建）。
3. 若你想修改 Markdown 并重新构建，先安装 [Python 3.10+](https://www.python.org/downloads/)；打开「终端」，进入解压后的目录：

```bash
cd ~/Documents/DIY/diy-lab
python3 -m pip install -r requirements.txt
python3 scripts/check.py
python3 scripts/build.py
open dist/index.html
# 如果浏览器阻止 file:// 页面访问本机进度存储，可改为：
python3 -m http.server 8000 --directory dist
# 然后浏览器访问 http://localhost:8000/
```

离线双击 HTML 可以看教程；若要跨章节可靠保存勾选进度，建议通过上面的本地 HTTP 服务访问。

除了用于把 Markdown 转成 HTML 的 **Mistune**，无需 Node、npm、数据库、Docker、VitePress 或长期运行的服务器。网页、搜索、勾选进度都能离线使用；浏览器进度只保存在本机。

## 第 2 步：克隆已经创建的 GitHub 仓库

本仓库已创建：<https://github.com/mayf3/diy-lab>。在 Mac 上使用：

```bash
git clone https://github.com/mayf3/diy-lab.git
cd diy-lab
python3 -m pip install -r requirements.txt
python3 scripts/check.py
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

浏览器访问 <http://localhost:8000/>。如果用的是下载的 ZIP，已包含首次构建的 `dist/` 供离线预览。

## 第 3 步：更新内容并发布网站

1. 修改 `content/` 下的 Markdown、`data/` 的卡片/视频数据，或 `source-data/` 中的采购 BOM。
2. 本地运行 `python3 scripts/check.py && python3 scripts/build.py && python3 scripts/verify_site.py`。
3. `git add . && git commit -m "Document DIY progress" && git push`。
4. GitHub Actions 自动构建并发布到 Pages；首次可能需要仓库 Settings → Pages → Source 选择 **GitHub Actions**。

**已验证 Pages 地址**：<https://mayf3.github.io/diy-lab/>；如后续修改未出现，查看 [Actions](https://github.com/mayf3/diy-lab/actions) 的自动部署状态。

## 仓库结构

```text
diy-lab/
├── README.md                  # 你正在读的说明
├── AGENTS.md                  # 给 Codex / WorkBuddy / 其他 Agent 的工作规则
├── CONTRIBUTING.md            # 编辑与审核规范
├── NOTICE.md                  # 权属和原始资料说明
├── data/
│   ├── projects.json          # 项目卡片与章节导航
│   └── videos.json            # 视频目录和 B 站链接
├── content/                   # Markdown 教程：一个文件就是一篇网页
│   ├── index.md               # 首页内容
│   ├── guide/                 # 新手指南 / 新建项目 / 素材规范
│   ├── videos/                # 视频工坊
│   └── projects/
│       ├── hachimodock/       # 13 关完整新手教程 + 日志
│       ├── halloween-costume/ # 已完成：待整理
│       ├── halloween-door/    # 已完成：待整理
│       └── christmas-magic-tent/ # 规划中
├── source-data/
│   └── hachimodock/bom.csv    # 可在 Excel/Numbers 中编辑的材料表
├── public/media/             # 仅放有授权的小照片与缩略图
├── templates/project/        # 以后每个新 DIY 都复用的模板
├── scripts/
│   ├── new_project.py        # 一键创建项目骨架
│   ├── check.py              # 内容质量/断链/BOM/真伪门禁
│   └── build.py              # 把 Markdown 编译成静态网页
├── assets/                    # 网站样式、浏览器交互、SVG 标志
├── .github/workflows/pages.yml # GitHub Pages 自动发布
└── dist/                      # 生成的网站（不提交到 Git）
```

## 最重要的制作理念：一步一关

每个正式教程章节至少写：**目标、准备、操作、验收、出问题怎么办**，附可勾选的检查项。每个项目有明确的“未做 / 制作中 / 已验证”状态。站内的勾选进度仅代表当前读者在本浏览器内学习到哪一步，**不等于作者真实通过了实物测试**。

### 复刻 HachimoDock：从这里开始

1. [理解项目与工具](content/projects/hachimodock/01-start.md)
2. [核对资料和版本](content/projects/hachimodock/02-sources.md)
3. [购物 BOM / 付款前兼容门禁](content/projects/hachimodock/03-bom.md)
4. [先模拟装配，再下单](content/projects/hachimodock/04-simulation.md)
5. [PCB 打样](content/projects/hachimodock/05-pcb.md)
6. [Bambu P1S 试打印](content/projects/hachimodock/06-print.md)
7. [焊接与裸机检查](content/projects/hachimodock/07-solder.md)
8. [Mac 固件烧录](content/projects/hachimodock/08-flash.md)
9. [客户端和 Codex](content/projects/hachimodock/09-desktop.md)
10. [实物装壳与验收](content/projects/hachimodock/10-assemble.md)
11. [故障树](content/projects/hachimodock/11-troubleshoot.md)
12. [拍摄/剪辑分镜](content/projects/hachimodock/12-video.md)
13. [制作日志与复盘](content/projects/hachimodock/13-log.md)

**当前执行中的采购工作：** [HachimoDock 分批询价与付款门禁](content/projects/hachimodock/purchase-plan.md)。

**特别注意：** HachimoDock 官方资料现有的 **芯片 v1/v3、屏幕 FFC、PCB_V1.2/机械键轴封装不一致** 风险，详见第 3、4 关；没明确核对前请勿下单。

## 为下一个 DIY 一键开新项目

```bash
python3 scripts/new_project.py mini-robot "我的第一个桌面小机器人"
python3 scripts/check.py
python3 scripts/build.py
open dist/index.html
```

新目录、Markdown 模板、购物表 CSV、视频目录和首页卡片都会创建；再编辑内容和 `data/videos.json`，即可发布新的教学内容。

## 视频怎样进入网站？

- 视频原片/4K 素材留在本地大硬盘，不要放在 GitHub 普通历史里。
- 自己拍摄并有权公开的小图压缩后放 `public/media/<project>/`，在 Markdown 中引用。
- 成片发布到 B 站/YouTube，打开 `data/videos.json`：设置 `status: "published"`，填 `video_url`，如果是 B 站视频还可以设 `embed: "bilibili"` 实现点击后加载的嵌入播放器。
- 尚未拍摄的视频只能标 `planned`，网页会清楚地显示“待拍摄”。

## 维护与协作

- 修改教程前先阅读 [AGENTS.md](AGENTS.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 每次重要内容修改运行 `python3 scripts/check.py`，不让断链、空 BOM 或假“已验证”通过 CI。
- 执行 `python3 scripts/build.py` 并在手机屏幕上检查内容（桌面浏览器开发者工具即可）。
- `content/guide/legal.md` 说明第三方资源许可。**此仓库目前不授予自己的文字/代码/设计统一开放许可证**；以后再由作者决定分别采用什么许可。不要把上游 HachimoDock 材料直接复制进来。

## 上游来源（2026-11-06 核对）

- HachimoDock 官方源码及文档：<https://github.com/YizhengWw/HachimoDock>
- HachimoDock 立创硬件复刻/BOM/PCB/STEP/装配视频：<https://oshwhub.com/eda_gqvzlprk/project_cnbmkbjc>
- 微雪 ESP32-P4-WIFI6 开发板：<https://docs.waveshare.com/ESP32-P4-WIFI6>

本仓库是**个人原创学习教程与进度记录**，不是原作者官方授权的设备套件。所有上游文档和素材的许可仍归其原始权利方。
