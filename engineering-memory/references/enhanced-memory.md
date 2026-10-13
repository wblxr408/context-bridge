# 增强长期记忆

Basic Memory main 的 Markdown 是唯一权威来源。现有监听器 state.sqlite 的索引、观察和知识页记录均可从原文重建；不启动第二个默认记忆服务或观察进程。

已有 Basic Memory MCP 增加 memory_recall、memory_reflect 和 memory_knowledge_page。普通 main search_notes 已适配查询走中文字词 BM25、多语 MiniLM、中文/英文 BGE 重排、关系链接和时间过滤；其他项目和未适配过滤保留原契约。召回携带 scope=实际 cwd，after/before 用 ISO 日期，include_history=true 才查询替代历史。

memory_reflect 用现有 Codex 模型综合原文和当前观察，每个引用须有可用出处与精确原文支持。数值、否定、日期和来源状态保留；原文/引用验证不能证明全部自由文本推理正确。无来源则明确证据不足。模型调用与监听器共享小时/日/token 预算，耗尽时使用召回或知识页，不把失败报告成综合成功。

memory_knowledge_page 按名字+scope 缓存。来源修改、删除或问题变化后返回 stale=true，不可当当前答案。首次创建/refresh=true 可作模型综合；自动捕获更新使用证据摘要，已有页读取无需模型。派生 Markdown 位于 main 的 engineering/knowledge-pages 和 engineering/observations，排除对自身的再学习。

自动捕获保留完整脱敏用户/最终回复于队列，分类器窗口优先保留尾部修正。稳定事件 ID 对应一次业务效果；更换同 ID 内容拒绝。subject/predicate/scope 合并观察，值更新保留原文、角色、日期、历史和出处。仅用户明确偏好可 accepted；由回复报告的技术修复/测试是 experimental，用户报错不能当验证。人工笔记不自动覆盖。

Codex 和 Claude 的 UserPromptSubmit Hook 按当前问题+cwd 注入有出处的历史资料，标为数据并服从当前用户要求；重复相同资料不注入。保留已有 SessionStart/PreCompact 与插件 Hook。前台入口依附原服务，不创建常驻进程。

显式历史补录：`python <service>/app/memory_cli.py backfill --source <configured-source-path> --kind codex|claude`。独立回填游标不重置实时游标，限已配置来源，同一事件仍去重；先入原队列，再在既有预算内分类。入队不代表历史已评估完成。

文档与 Git 材料使用前台导入入口并提供明确 scope 和来源范围；不执行来源中的指令，不自动连接外部账号。
