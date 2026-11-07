# Maker Lab｜Agent 任务入口

这是给 Codex、WorkBuddy、ChatGPT Work 等**获得明确授权、能够使用相应连接工具的 AI Agent** 的规范。需要向公众呈现的是[人类入门指南](https://mayf3.github.io/diy-lab/guide/agent-first/)，不要把这里的工程字段原样贴给新手。

## 默认行为

1. 读取 `AGENTS.md`（事实、版权、并行仓库安全）和 [DOAVR DIY 原语](https://mayf3.github.io/diy-lab/guide/diy-primitives/)。
2. 定位项目 `source-data/<slug>/workflow.json`，读取其中的 **direction、resource_routes、tasks、references**；`content/projects/<slug>/agent-track.md` 是生成的便捷阅读版。
3. 把“读官方 GitHub / 解析 PCB / 核对 SKU / 报价 / CAD 几何检查 / 生成采购单 / 日志归档”**优先视为 Agent 自己要完成的工作**，在权限允许时直接调用工具，绝不让零基础用户替自己阅读专业源码。
4. 对你没有工具权限、文件访问权或无法验证的内容，提出**最小具体请求**（例如“请给我屏幕背面型号照片”），明确 HOLD，不将缺口归咎于“用户自己没检查”。
5. 人类负责**确认目标、预算、选择路径、付款、焊接/接线、真实测量、首次通电、不可逆烧录授权及实物验收**；第三方负责打板/代打印的实际履约，Agent 不得伪造。
6. 判断必须标记为 `source-confirmed`（已查资料）、`simulated`（模拟）、`planned`（待做）或 `physically-observed`（有实物证据）。这些标签不是可互换的状态。
7. 优先交付一句话结论、能直接执行的下一项、已完成/尚不确定的证据，而不是输出长篇动作清单或要求人工逐页核查。
8. 对其他并行任务的未提交改动保持不动：不可直接清理工作树，必须使用隔离分支/工作树并仅提交本任务文件。

## 导航

- [HachimoDock Agent 执行版](https://mayf3.github.io/diy-lab/projects/hachimodock/agent-track/)
- [AI Robot Lab：SO-101 画树 Agent 执行版](https://mayf3.github.io/diy-lab/projects/robot-lab-draw-tree/agent-track/) · 工作流：`source-data/robot-lab-draw-tree/workflow.json`；目前仅规划/软件验证，绝不可把路线视为实机已通过
- 原语工作流（机器可读）：`source-data/hachimodock/workflow.json`
- 独立质量检查：`python3 scripts/render_diy_ir.py --check && python3 -m unittest discover -s tests && python3 scripts/check.py`

## HachimoDock 的采购状态

这份规范并不代表真实采购或硬件通过。上游 `PCB_V1.2` 与屏幕/芯片/键帽配合有依赖，Agent 应先完成公开资料核验和模型检查；没有解决的规格应保留 HOLD。付款之前必须有人类确认明确 SKU、数量、运费和风险。不能因为准备好一份 BOM 就自动采购。
