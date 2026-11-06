# Maker Lab 已经发布：如何继续维护

> **2026-11-06 已验证上线：** [GitHub 仓库](https://github.com/mayf3/diy-lab) · [中文教程网站](https://mayf3.github.io/diy-lab/)。不需要再新建一个仓库。

## 更新教程：新手最短流程

1. 在 Mac 终端执行 `git clone https://github.com/mayf3/diy-lab.git`（已经克隆过则直接打开原目录）。
2. 找到要改的章节，如 `content/projects/hachimodock/purchase-plan.md`；用任何文本编辑器修改 Markdown。
3. 在仓库根目录运行 `python3 scripts/check.py`，确认无断链或缺少检查项。
4. 如果需要本地预览，安装 `pip install -r requirements.txt`，运行 `python3 scripts/build.py`，再用 `python3 -m http.server 8000 --directory dist` 打开 <http://localhost:8000/>。
5. 提交：`git add . && git commit -m "Update DIY log" && git push`。GitHub Actions 会自动重建并发布到 [网站](https://mayf3.github.io/diy-lab/)。
6. 打开 [Actions 页面](https://github.com/mayf3/diy-lab/actions) 看是否部署成功；网页一般在发布后稍有缓存延迟。

## 做 HachimoDock 时怎么持续记录？

- [采购门禁 Issue #1](https://github.com/mayf3/diy-lab/issues/1)：核对主控芯片版本、屏幕排线、轴体和 PCB 兼容性；**证据齐全再付款**。
- [结构模拟 Issue #2](https://github.com/mayf3/diy-lab/issues/2)：下载 STEP、EDA 3D 和尺寸图，逐项检查机壳内干涉。
- [采购执行单](/projects/hachimodock/purchase-plan/)：每次询价后更新 `source-data/hachimodock/bom.csv` 的状态和金额。
- [制作日志](/projects/hachimodock/13-log/)：每次实测写日期、方法、结果、照片来源，别把尚未测试的事情改为“已完成”。

## 私人信息、源文件与视频

- 只公开有授权的作品照片、自己创作的源文件或不涉及私人信息的日志；第三方 STEP/固件/装配视频保持官方链接。
- 不上传孩子的可识别面部、学校、订单地址、支付信息、API 密钥或完整聊天日志。
- 4K 原片留在本地硬盘，成片上 B 站，更新 `data/videos.json` 链接。

## 不会影响已有仓库

本项目独立部署，不覆盖已有博客、个人主页或其他代码项目。
