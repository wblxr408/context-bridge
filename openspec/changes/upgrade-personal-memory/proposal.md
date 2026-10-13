# 个人长期记忆与交接升级

## Why
中文自然问句找不回已存在记忆，自动捕获截断最新要求、经验整理不足，context-bridge 新政策与旧哈希交接协议冲突。

## What Changes
修复中文检索/布尔查询/结果去重/最新约定选择，增加多语向量与重排、图和时间召回、带原文证据的事实合并、持续知识页、反思、项目范围、原生提示注入与可恢复历史导入；修复交接版本绑定和旧指南一致性。

## Capabilities
- multilingual-recall
- grounded-consolidation
- materialized-knowledge
- native-memory-integration
- semantic-handoff

## Impact
扩展已有工程记忆服务与 Basic Memory stdio 适配器；唯一权威资料仍是 main Markdown。沿用监听器状态库作可重建索引、队列和来源台账。全局安装需权限；OpenSpec CLI 原生 realpath 遇到沙箱 EPERM 时使用仍解析符号链接的标准 realpath 回退；已完成初始化和 apply 任务解析。
