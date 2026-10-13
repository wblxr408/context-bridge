# 检查点保留与两阶段回收

只管理用户明确指定的独立任务检查点根目录。保留 current、last_received、最近版本、pinned、in_use，以及所有依赖；没有确认所有读者停止的包不得回收。未知目录、资料不全和来源异常全部保留。不得扫描删除其他任务、工作树、Git 历史或 Basic Memory。

当前注册 schema=2。`.retention.json` 包含 task_id、递增 revision、current、last_received、policy 和 items。每项有 id、snapshot_id（task-id/revision-id）、created_utc（时区）、lifecycle（active/received/retired/trash/deleted）、pinned、in_use、self_contained、depends_on。旧包还须 no_readers_confirmed=true 和 superseded_by，替代包必须在保留集合、时间更新、要求覆盖完整。新包账本 task_id/snapshot_id 须与注册一致。旧 schema=1 注册保持原状；迁移须对照包原文与实际读者状态，不能凭旧哈希推断新版本身份。

默认保留最近3个、至少7天、隔离7天、软预算512MiB。体积用于容量报告，不用作内容或行为验收。超出预算不绕过保护规则。self_contained 是依赖审查声明，机器不能证明全部自然语言依赖。

1. `python <skill>/scripts/retention.py plan <absolute-task-root> --out <outside-plan.json>` 生成 plan_id、登记修订、保护原因和候选。
2. 核对任务、版本、读者状态和覆盖后执行 `python <skill>/scripts/retention.py apply <absolute-task-root> --plan <outside-plan.json> --plan-id <returned-plan-id>`。
3. apply 在协作锁内重新核对登记与保护状态；登记/候选变化拒绝旧计划。首阶段只移到 `.trash`；隔离期结束后新计划才可 purge。实际移动删除前重新解析源/目标，拒绝链接和其他目录。

执行中断时 `.retention.pending.json` 保留原计划。先核对实际源/目标、登记和读者状态，修复登记并保留审计副本，再恢复；不得盲目重试或删除未知数据。隔离恢复针对明确检查点，确认没有链接和目标冲突后移回同一任务根，更新 retired 并设置 in_use/pinned。已 purge 内容依赖其他备份恢复。

`legacy-retention.py` 保留旧包显式迁移资源，当前技能不把它作为默认清理或验收路径。
