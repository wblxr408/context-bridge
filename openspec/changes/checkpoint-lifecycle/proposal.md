# Proposal

## Why

用户授权部署最新checkpoint生命周期并尽量清理80%，同时保留受保护恢复点。现有保留脚本只管理本地包；Basic Memory快照需要历史摘要、检索隔离和可恢复生命周期。

## What Changes

- 复用最新v4规划：普通原件24小时/隔离72小时；数量或明确批量清理快速通道免等一天，采用60分钟隔离默认。
- 确证agent/session归组，未知身份、固定、实际使用、最新未完成恢复点及明确原文依赖受保护；80%为尽力目标。
- 每任务保存tokenizer计量的历史摘要，按需查询并排除自动注入；不建立长期完整原文归档。
- 精确计划、语义复核、隔离、恢复、期限删除、旧游标状态与索引卸载在既有服务中实现；复用原监听器维护，不另建服务。

## Capabilities

### New Capabilities
- `checkpoint-lifecycle`: BM检查点登记、受保护清理、历史摘要、隔离恢复与到期删除。

### Modified Capabilities
无已归档规格变更。

## Impact

现有memory_runtime/integration、MCP代理、监听器和CLI及context-bridge/engineering-memory规则；main仍为唯一权威Markdown。原历史模型队列清理已取消，本次不清空队列或预算，不实现另一规划中的普通知识每日/每周合并。快速60分钟为本次部署采用的可调默认。
