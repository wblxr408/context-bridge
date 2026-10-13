# 要求账本：仅编写、核对或排错时读取

## 编写

`requirements.json` 的 schema=1，包含 task_id、snapshot_id（如 task-example/revision-2）、requirements 数组。ID 在同一任务内稳定，内容变化提升 revision；撤销/替代保留旧记录，status=superseded 并填写 superseded_by。新包注明前一包路径与 snapshot_id；不可从压缩摘要重新发明用户要求。

示例需替换为实际内容：

```json
{
  "schema": 1,
  "task_id": "task-example",
  "snapshot_id": "task-example/revision-2",
  "requirements": [{
    "id": "R001", "revision": 1, "status": "active",
    "kind": "constraint", "scope": "global", "always_load": true,
    "statement": "技能必须按当前阶段渐进式加载。",
    "source": {"path": "evidence/user-request.md", "quote": "我要skill也是渐进式加载", "locator": "用户消息，2026-09-27"},
    "acceptance": "常规判断只读取入口和 decision；恢复不读取制包说明。",
    "progress": "pending", "evidence": []
  }]
}
```

kind 为 goal / constraint / deliverable；status 为 active / superseded；progress 为 pending / in_progress / done。goal 和 constraint 必须 always_load=true；其他要求填写具体 scope。done 必须有 evidence 数组，元素为包内文件路径。superseded_by 引用账本中的其他 ID。

source.path 指向包内 UTF-8 原文，quote 必须原样出现在文件中，locator 定位消息/段落。证据缺失时不能编造原文；先做标明不完整的应急 checkpoint，不封为可交接包。脚本无法证明所有用户要求都被录入；模型仍须对照可见原始请求逐条检查漏项。

执行 `python <skill>/scripts/requirements.py check <bundle>`。有前一版本时增加 `--previous <previous-bundle>`，检查 ID 未丢失、修订未倒退、内容变化提升 revision。对照前一版本的原始要求与当前工作状态。

## 当前工作块

`python <skill>/scripts/requirements.py brief <bundle> --scope <scope>`

brief 仅输出全局目标/约束和当前 scope 的 ID、revision、statement、验收标准与原文定位，报告推迟项数量，不输出全部历史。scope 不存在则拒绝，避免拼写错误漏读。发现推迟项是当前依赖时修正 scope 并制作新包，不能忽略真实依赖。

## 接收回执

在包外写 receipt.json，含 task_id、snapshot_id、scope、checks 数组。checks 必须恰好覆盖 brief 的全部 ID；每项含 id、revision、result（aligned / conflict / unknown）、interpretation、next_action。aligned 需比较原文含义和实际下一步后填写，不能批量伪造。conflict/unknown 均阻止接管。

`python <skill>/scripts/requirements.py receipt <bundle> --scope <scope> --receipt <absolute-receipt.json> --snapshot-id <task-id/revision-id>`

脚本核对来源原文、task/version/scope 和逐条覆盖，无法判断自然语言 interpretation 是否真正正确。验收证据存在不等于测试通过，仍要阅读对应证据。必要资料缺失或冲突先解决，不能绕过回执检查进入写入。
