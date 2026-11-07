# 如何给 Maker Lab 新增一个 DIY 项目

无论是 3D 打印的小玩具、纸工、帐篷，还是更复杂的电子作品，都用同一套骨架。新手不必修改网站前端。

## 一、给作品取名

名字用一句中文说明“做什么”；英文目录名只用小写英文字母、数字和短横线。例如 `mini-robot-desk`。

## 二、用命令创建项目

**Agent-first 增强：** 新项目脚本还会生成一份 `source-data/<slug>/workflow.json` 轻量原语，以及两份从该数据生成的人类/Agent 制作流程。初始内容全是 `planned`，尚未验证，需 Agent 填写具体任务后发布。参见 [DIY 原语规范](/guide/diy-primitives/)。



在仓库根目录打开终端（需要 Python 3.10+）：

```bash
python3 scripts/new_project.py mini-robot-desk "桌面小机器人"
```

脚本会复制 `templates/project/`，在 `content/projects/mini-robot-desk/` 生成基础教程，并把新项目登记到 `data/projects.json`，自动出现在首页目录和侧边导航。还会生成 `source-data/mini-robot-desk/workflow.json`、`human-track.md` 和 `agent-track.md`；这两个教程视图来自同一份工作流。

## 三、把空白模板替换成真实步骤

- **目标**：最后要做成什么、给谁用、如何判定成功。
- **开始前**：设备、技能、预算、耗材、预计时间。
- **材料表**：精确 SKU、来源、必要性、数量、价格、当前采购状态。
- **风险门禁**：哪些信息不确定时绝对不能付款/通电/打印整件。
- **操作**：一行只做一个动作，提供操作结果照片，而不仅是“安装好”。
- **验收**：能测量、能观察、最好有证据的通过条件。
- **排错**：第一次可能卡在哪里，先排查什么，什么时候停止。
- **视频**：拍摄计划、成片链接、对应的教程版本。
- **复盘**：真实成本、耗时、失败和修订。

## 四、检查与预览

```bash
python3 -m pip install -r requirements.txt
python3 scripts/check.py
python3 scripts/build.py
```

然后在文件管理器打开 `dist/index.html` 即可离线查看。上传 GitHub 后，GitHub Actions 会重新运行这两个脚本并发布到 Pages。

## 五、更新状态不要靠感觉

状态字段位于 `data/projects.json`：

| 状态值 | 站点显示 | 允许的事实陈述 |
| --- | --- | --- |
| `planning` | 规划中 | 只承诺方案与风险，不承诺已做出来 |
| `preparing` | 准备中 | 已建立教程、正在核实材料 |
| `building` | 制作中 | 有部分实物/测试记录 |
| `verified` | 已验证 | 关键验收已做并有可复核记录 |
| `completed-unwritten` | 已完成·待整理 | 实物完成，但教程尚未整理到可复刻 |
| `archived` | 已归档 | 停止维护或被新版取代 |

**禁止仅因 Markdown 写完就标记 `verified`。**

[查看项目模板说明](/guide/media/) · [返回项目目录](/projects/)
