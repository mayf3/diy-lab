# 在外面取得嘉立创免费激活文件

工作台和设计资料整理可以先使用。EDA 的实际工程创建，需要先完成本人账号的客户端激活。

1. 在手机浏览器打开 https://lceda.cn/page/desktop-client-activation 。
2. 登录你自己的嘉立创账号，下载免费激活 `.txt` 文件。
3. 把原始文件作为附件发到当前对话，后续由 Agent 在 Mac 走正常导入并验证编辑器。

官方支持下载文件后导入客户端，或粘贴其全部内容。由此可将“取得文件”和“在 Mac 导入”分开做；本轮尚未实测手机页面。若手机浏览器无法下载，可以尝试浏览器的桌面网站显示。

激活文件含账户信息，保持原样、不要放进代码仓库或公开工作台。无需提供账号密码。本工作台不接收或保存激活文件，也没有伪造“自动激活”按钮。

当前 Mac 上观察到的是首次激活窗口。后续必须以真实编辑器工程操作验收，不能只凭 `doctor` 或 MCP 连接通过判断已激活。此前远程 GUI 操作遇到 macOS 辅助功能权限限制，收到合法文件后仍需确认正常导入是否能完成。

资料核查日期：2026-11-26。官方依据：

- [中文客户端常见问题](https://prodocs.lceda.cn/cn/faq/client/)
- [英文客户端 FAQ：Load Activation File](https://prodocs.lceda.cn/en/faq/client/)
- [官方 CLI：activate 仅唤起窗口，不是许可证激活](https://prodocs.lceda.cn/cn/api/guide/cli.html)
