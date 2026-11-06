# Maker Lab 最简单的开始方式（1 分钟）

**这是完整的 GitHub 仓库源文件，同时附带一个已经生成的网站。**

1. 解压 `diy-lab-repo.zip`，打开里面的 **`diy-lab/dist/index.html`**，先看网站。若浏览器阻止本地功能，可在 Mac 终端进入 `diy-lab/`，输入 `python3 -m http.server 8000 --directory dist`，再打开 <http://localhost:8000/>。
2. 第一个项目是 **HachimoDock**。打开首页的「开始第一个项目」，先完成“原始资料与兼容性”关卡，**先不要买 PCB、机械轴或屏幕**。
3. 公开 GitHub 仓库已创建：<https://github.com/mayf3/diy-lab>；完整仓库请直接 clone，无需重新创建。
4. GitHub Pages 已启用并上线：<https://mayf3.github.io/diy-lab/>；以后每次推送 Markdown 就会自动更新网站。
5. 想做新的 DIY：在根目录执行 `python3 scripts/new_project.py my-new-project "我的新作品"`，再编辑自动生成的教程和购物清单。

如需分发给完全不懂 Git 的朋友，只给他们 **GitHub Pages 网站地址** 即可；不需要朋友安装任何开发工具。
