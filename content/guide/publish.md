# 把 Maker Lab 发布成 GitHub 网站

## 目标

让 GitHub 仓库同时成为**公开可阅读的网站**。不需要购买服务器、域名或部署数据库。

## 首次发布

1. 下载整个 Starter ZIP，解压并在本机打开 `dist/index.html`，检查中文显示。
2. 打开 [GitHub 新建仓库](https://github.com/new)，输入 `diy-lab`，选 Public，**不要**自动初始化 README / License。
3. 在解压后的仓库目录执行（替换自己的 GitHub 用户名）：

```bash
git init
git branch -M main
git add .
git commit -m "Initial Maker Lab: HachimoDock guide"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/diy-lab.git
git push -u origin main
```
4. 进入新仓库 `Settings → Pages → Source → GitHub Actions`。
5. `main` 分支的每次 Push 都会运行 `scripts/check.py`，通过后才会执行 `scripts/build.py` 并发布 Pages。
6. 站点地址一般是 `https://<你的用户名>.github.io/diy-lab/`，以 GitHub 显示的 Pages 地址为准。

## 内容更新

改 Markdown → `python3 scripts/check.py` → `python3 scripts/build.py` → 本地预览 → `git add .` / `git commit` / `git push`。不要上传 `dist/`、原始 4K 视频或任何敏感凭据。

## 不会影响已有仓库

本项目作为一个独立新仓库部署，不覆盖你已有的博客、个人主页或其他代码项目。未来如需迁移到自定义域名，再单独配置。
