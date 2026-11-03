# 参赛演示与提交材料

本文件是可填写的材料，不代表已提交、资格已获确认或视频已录制。
规则与报名页：[Developers Wilding](https://otari.ai/devs-wilding)。
评分原文：[Judging Rubric](https://docs.google.com/document/d/1-spnCZ3f2SSki8cb6FnochjchdyttUsjjxfoE6aBnF4/edit)。

2026-11-03 复核 Rubric：开放权重模型最多 30 分、实际使用的 Otari 功能最多 60 分、
项目与演示 10 分。每个高级功能 10 分；仅仪表盘启用不计分。
演示与视频反馈须由参赛者本人带音频录屏，不可使用 AI 视频。

## 项目说明草稿

**Bridge: evidence-backed memory that can resume.**

Bridge turns a conversation into source-backed personal memory, checks it against
current official documentation, and produces answers with inspectable quotations.
When a model request fails or a budget is exhausted, the task keeps its evidence
and prepared requests so the user can continue without rebuilding the investigation.

The competition branch adds Otari-hosted inference to the existing extraction and
reflection boundaries. Separate model roles handle memory extraction, grounded
synthesis and tool use. The workbench displays request identifiers, actual models,
fallback reports, tool records and reported or unknown costs. A separate authenticated
HTTP MCP service publishes only selected read-only sources and revisions.

**Before submission, replace planned capability claims with the actual hosted results.**
At present the implementation and local contracts are complete; hosted model/tool,
routing and spending-limit results have not yet been collected.

## 4 分钟真人演示提纲

| 时间 | 操作与讲解 | 画面要呈现的证据 |
| --- | --- | --- |
| 0:00–0:25 | 解释长期记忆容易失去出处、失败后需要重做的问题；介绍 Bridge | 问题与完整工作台 |
| 0:25–1:05 | 粘贴演示对话，使用第一个开放权重模型提取；输入明确修正 | 原句、当前事实、提取请求与模型 |
| 1:05–1:55 | 问 `lru_cache` 能否保证并发只执行一次，启用官方网页核对 | 实际 Otari 搜索、允许域名、快照、第二模型综合与精确引用 |
| 1:55–2:30 | 展开代码分析与调用账本 | 实际代码/stdout/exit code，网关费用及未知值 |
| 2:30–3:10 | 展示已取得的真实回退与预算拒绝；继续已暂停任务 | Otari 活动记录、相同 operation key、保存的来源与恢复结果 |
| 3:10–3:40 | 实际使用 HTTPS MCP 搜索和读取已发布原文 | 完成的 MCP 调用、来源版本、原文参与回答 |
| 3:40–4:00 | 说明不足证据行为、已知限制与 Otari 集成价值 | 不足证据任务与实际完成范围 |

录制前先取得所有要声称的真实结果。缺少的能力应从讲稿中删除或明确说尚未完成。
不要展示凭据、个人聊天或未批准发布的记忆。本人实际操作并配音录屏，长度 3–5 分钟；
不生成或伪造参赛者演示视频。本文件没有替参赛者录制任何媒体。

## 书面反馈草稿（待真实使用后填写）

**Integration:** An OpenAI-compatible transport let the existing memory boundary
adopt Otari without replacing retrieval or the Markdown knowledge base. Persisting
the exact request and idempotency key is valuable for interrupted research tasks.

**Observability:** Request IDs, routing headers, reported cost and gateway tool records
are the fields the application needs to distinguish model prose from execution.
During development, cached documentation and the live repository described different
Chat Completions tool-record coverage; we used current repository text and retained an
explicit unverified state when records were absent. Hosted behavior is still to be confirmed.

**After hosted use:** Add the model names, a real request ID, what worked well, the most
important actual issue, its reproducible steps, and one concrete improvement suggestion.
Do not submit placeholder opinions as completed hands-on feedback.

## 提交清单

- 报名邮件线程中确认迟报名资格和截止时区；账户创建不能替代参赛确认。
- 按官方要求，回复原报名邮件线程；尚未在本轮发送提交邮件。
- 项目说明与参赛 Otari 邮箱：`YOUR_OTARI_EMAIL`。
- 公开仓库：`https://github.com/wblxr408/context-bridge`。
- 比赛分支：`codex/otari-devs-wilding`。
- 首个 Otari 提交：`https://github.com/wblxr408/context-bridge/commit/2177c03`。
- 只列实际完成并在应用使用的 Otari 能力，附真实任务/请求证据。
- Otari issue/PR 链接（若实际创建；当前无）。
- 3–5 分钟参赛者本人演示视频链接：待录制。
- 本人反馈录屏或补充实际体验后的书面反馈。
- 核对官方提交要求是否变化；此前规则中的截止为 11 月 11 日 23:59，时区待主办方确认。

## 邮件正文模板

```text
Project: Bridge — evidence-backed memory that can resume
Otari account email: YOUR_OTARI_EMAIL
Repository: https://github.com/wblxr408/context-bridge
Hackathon branch: codex/otari-devs-wilding
First Otari commit: https://github.com/wblxr408/context-bridge/commit/2177c03

Description:
[Use the project description above, updated to the actual completed behavior.]

Otari capabilities actually demonstrated:
[Only the capabilities supported by real hosted application evidence.]

Otari contribution (if any): [actual issue/PR link, or none]
Participant-recorded demo (3–5 minutes): [URL]
Feedback: [participant recording or actual written feedback]
Known limitations: [actual remaining limits]
```
