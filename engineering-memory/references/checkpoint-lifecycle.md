# Basic Memory checkpoint 生命周期

这是 main 中 codex_session/coding_session 原件的独立分支。原 retention.py 继续只管理注册 local bundles，不将 vault 传给它。入口为既有 engineering-memory 服务 app/memory_cli.py；复用同一 listener、MCP、SQLite 派生缓存及 main Markdown。

计划默认普通通道：原件至少24小时，隔离72小时。`--lane count` 对同任务超过8份保留3份、同 cwd 超过20份保留10份，保护规则优先；`--lane fast --fraction .8` 是明确批量请求，免等24小时，默认隔离60分钟，可通过 checkpoint_fast_quarantine_minutes 配置。百分比不是硬性指标。监听器启动时立即处理已到期批准项，之后沿用既有维护周期；维护仅完成已批准隔离，不自行推断摘要或批准新删除。

精确 agent/session/cwd 分组。保留最新恢复点、pinned、in_use、依赖原件、未知身份/时间/目录；通过 `--active-session` 保护活动聊天，已固定聊天也可这样保护。保留最新完成点是当前保守实现；不因 age 或 notLoaded 推断完成。历史 continues 链接不自动等于原件依赖，显式 depends_on 才参与保护。缺少语义覆盖 review 的原件不进入候选。

操作前编写 review JSON：每个精确 permalink 对应非空 coverage，说明原件独有目标、结果、失败、数值修正和未完成要求保存在何处；还须 no_readers_confirmed=true 及非空 reader_evidence，记录实际读者核对依据，不能从内容已替代推断无人使用。`checkpoint-plan --review <review.json> --lane fast --fraction .8 --active-session <id>` 输出精确计划。保存 stdout 后，以 plan.candidates 的 group 为键提供 drafts JSON：body、reviewed=true、sources（本组精确候选 permalink）、短于1000 token时的 short_history_reason；更新已有摘要还须 previous_version 并将已有历史合入新稿。摘要不能只是标题列表，不强行填充无事实内容。

摘要使用配置 checkpoint_tokenizer 指向的固定本地 tokenizer.json，关闭截断与填充，计量整个Markdown。通常1000–2000 tokens，真实短历史可更短；超过2000、来源不全、版本变化均拒绝。摘要 type=checkpoint_history、historical=true、auto_inject=false；当前召回、反思、知识页、UserPromptSubmit、自动context不使用它。原生 SessionStart/PreCompact 按 session/task/decision 类型查询，历史摘要类型不匹配。显式 `memory_recall(include_history=true)` 或 search_notes 的 checkpoint_history 类型查询可检索历史。

同任务更新摘要时，先将上一版历史摘要保存到服务 checkpoint-summary-revisions，再记录已审核新版的发布事务。新稿回读成功后同步本组既有隔离记录的摘要版本，保持原有原件到期时间；写入后中断可据事务继续完成。上一版摘要仅临时保留至相关隔离批次的最晚期限，当前摘要版本异常时停止清理旧版；按登记的精确路径逐文件删除。发布事务只暂存摘要正文，不保存checkpoint原件全文。

`checkpoint-apply --source <plan.json> --drafts <drafts.json>` 先保存并读回全部摘要，再在锁和操作记录保护下移至服务 checkpoint-quarantine。原件离开热库，清理其向量、页/注入缓存、引用它的服务自有派生页，并调用 Basic Memory 原生项目增量索引清除孤立记录。协调器每次都会核对被删除路径，无需强制重建全部未变化笔记。失败保留隔离原件，原生索引未成功时不允许永久删除。可重试恢复已记录的部分移动，但必须查看返回 expected、quarantined、state；partial 需要重新规划尚未移动的原件。

`checkpoint-restore <exact-permalink>` 拒绝覆盖冲突，恢复后固定。精确 read_note/read_content 在隔离期返回原件和隔离状态；永久删除后返回墓碑、摘要路径和期限，不静默替换为最新。`checkpoint-purge` 或既有 listener 的300秒维护周期，在真实期限后重新检查保护、摘要版本、隔离原件身份，逐文件删除。摘要被改动、出现原件依赖或索引同步失败会阻止删除，需人工复核。此处“人工”包括当前任务中有原文证据的前台审核。

登记文件 checkpoint-lifecycle.json 不保存原件正文。备份仅代码、配置和必要状态，不建立长期原件归档。隔离不减少原件占用的磁盘空间，purge 才释放；不承诺内存立刻下降或撤回已进入其他聊天上下文的内容。当前已打开的 MCP 进程需要重新连接才能加载新代理代码。
