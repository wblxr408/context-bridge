## 只加载当前分支

| 当前动作 | 首次只读 |
|---|---|
| 判断是否迁移 | [decision.md](references/decision.md) |
| 保存 checkpoint | [handoff.md](references/handoff.md) |
| 从指定 checkpoint 恢复 | [resume.md](references/resume.md) |
| 管理 checkpoint 占用 | [retention.md](references/retention.md) |
| 配置触发或解释设计 | [integration.md](references/integration.md) |
| 跨 Codex/Claude 使用或运行环境问题 | [hosts.md](references/hosts.md) |

禁止一次读取整个技能目录、全部 references 或所有脚本。每一步只读该分支指定的下一份说明；执行脚本无需读取源码，排错才按函数定位。已读且未变化的说明复用，不重复灌入。

普通短任务直接继续。长任务在阶段完成、约束遗漏、大批读取或压缩通知时评估；无新信号不反复评估。

保留原目标、最新修正和授权范围。checkpoint 不代表任务完成。只有用户明确要求新建对话时才调用创建工具。迁移前停稳源端写入；接收端完成版本、要求覆盖和现场检查后接管。旧包只按保留策略回收，不覆盖封包或回滚工作文件。
