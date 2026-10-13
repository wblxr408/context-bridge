# Design

## Architecture
existing Basic Memory bridge → enhanced main recall and grounded memory tools → existing vault + existing listener state database。其他项目或未适配搜索契约透传原服务。新增模块嵌入已有监听器，不创建第二默认服务或知识库。

## Retrieval
中文字词组合 BM25 与多语向量召回经 RRF 融合，链接图扩展、日期/状态/项目过滤，按 canonical permalink 去重后重排。已替代决定默认不用于当前答案，历史检索显式开启。来源状态和出处随结果返回；没有证据时明确无法回答。

## Consolidation and pages
稳定事件 ID 绑定原载荷，重试产生一次业务效果，改变同 ID 的载荷拒绝。subject/predicate/scope 为可持续观察键；每项结论保留来源角色、原文、日期、值与历史。按事实时间更新，不让迟到旧消息覆盖新约定；不同数字和否定保留为变化。人工笔记不自动覆盖。

知识页在 main 的 engineering/knowledge-pages 保存问题、引用和版本，新增/删除事实使其过期。反思先查知识页/观察/原文，可用现有 Codex 模型作有出处综合，校验每项来源引用。读取现成知识页无需模型调用。

## Continuity
显式 task_id/snapshot_id 绑定账本、回执和所有权转交；要求修订与解释覆盖保留。旧哈希接口仅迁移兼容，不作为新交接流程。合作式锁不阻止协议外编辑。

## Rollout
先完成行为失败、实现、回归和真实语料评估，再备份并按授权安装。2026-10-12已安装到全局Codex和Claude Code，同一任务已恢复，原生多语迁移374实体且0错误。实际双配置MCP路由与Codex原生模型业务通过；Claude原生模型遇到现有推理网关503，保留为未完成验收，保持用户提供方配置。

安装及恢复必须取得既有listener.lock并持有至改动完成，计划任务Disabled不代表旧写入者退出。SQLite恢复使用备份API处理活动WAL；不把复制主文件当作完成状态恢复。显式失败恢复保留审计与预算，并按已保存结果选择恢复状态。历史补录分别报告新增事件、排队和过滤，后台继续原调用预算。
