# Otari 托管验收 · 2026-11-03

在本机 Windows 的独立比赛克隆 `D:/context-bridge-otari` 中运行真实应用流程，
请求发往 `https://otari.ai/api/v1`。材料全部为虚构退款服务约定和公开 Python 文档。
用户授权总额 USD 0.20，并单独批准临时公开一份演示笔记供 Otari MCP 读取。
本报告不代表主办方评分、资格确认或提交成功。

## 结果

| 场景 | 实际结果 | 可回查的任务 / Otari 请求 |
| --- | --- | --- |
| 对话提取 → 落库 → 原句回答 | Qwen3.5 提取明确用户偏好，Qwen3 综合并精确引用新记忆 | `878bb7f32c5f44e0ac2b685bb2990aa2`；提取 `d57b2f25-3f5e-4d30-ad18-a7df053ce047`，综合 `47ef6732-4f1d-4c71-ae42-69021fead9c4` |
| 官方网页搜索与引用 | 实际 Otari `web_search` 完成，应用保存 Python 官方网页正文 r2，回答否定“并发只执行一次”，原句匹配通过 | `04b733694e2a499bb9b4c74813009557`；搜索 `c0137439-96b9-432d-85f3-2cec85ddeb96`，综合 `98a1a063-3015-4537-b808-db28b4a3f6cf` |
| 代码分析 | Otari 沙箱返回实际 code、stdout、stderr 和退出码 0；计算与该任务分析前账本中的 USD 0.000268、1588 输入 / 364 输出 tokens 一致 | `cd43491162b74ce38da527816ccd47e2`；执行 ID `otari_srvtoolu_059ae686cee7408ca606878428e86298`；请求见 JSON |
| 远程 MCP | 经 Otari 完成远程搜索和 `read_source`，带版本原文进入任务；一份回答采用 `remote/…` 引用 | `3383c290aa8442cba7632b83b4970440`；请求和工具 ID 见 JSON |
| 服务端预算拒绝 → 原任务继续 | 同一工作区预算临时降至 0，收到 HTTP 403 `budget_exceeded`，任务暂停；恢复 0.20 后原任务完成，操作键保留 | `f47c21a8f55345a896ea02f89c717d1f`；拒绝请求 `0cbb9029-2287-4d51-99f4-eb5b642bfb64` |
| 路由策略 | 应用以 `bridge-contest-reflect` 调用，实际由 Nebius Qwen3 服务；策略配置 DeepInfra Qwen3.5 备用 | `ff49862cfafb417cb2892dc7851f9f2d`；`6d2eb557-6288-49d8-86fb-258e5a7e470f`，fallback=false，attempt_count=1 |
| 真正供应商回退 | **未验证**。尝试在该独立策略临时设置不可用主模型，被 Otari 保存前校验拒绝；正常主备配置保留。随后调用仍是主模型成功，不能称为回退 | `50615492ed4e401da51337b71eee35a6`，fallback=false |

机器可读的已脱敏证据：[otari-hosted-evidence.json](otari-hosted-evidence.json)。
完整本机任务仍在忽略的 `local-state/otari.sqlite`；公开报告不包含凭据、原始推理文本或整页网页副本。

## 模型与费用

提取使用 `alibaba/qwen-3.5-35b-a3b`，实际为 DeepInfra 的 Qwen/Qwen3.5-35B-A3B；
综合、搜索、MCP、分析使用 `alibaba/qwen3-30b-a3b-instruct-2507`，实际为 Nebius 的
Qwen/Qwen3-30B-A3B-Instruct-2507。两个官方模型卡均标 Apache-2.0：
[Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)、
[Qwen3 Instruct](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)。
这是不同生成模型的实际职责分工证据，最终计分由评委决定。

- 应用账本的最终已报告费用：**USD 0.074598**，未知费用调用 0。
- 额外接口排查调用：**USD 0.011151**，由实际流式 usage 回报；不在应用任务账本中。
- 本轮已报告总额：**USD 0.085749**，包含失败探索及上项排查费用；低于授权 0.20。
- Otari 工作区花费上限最终保留 **USD 0.20 / Never reset / Every provider**。
  同一预算的已用金额从未清零，页面按美分显示约 USD 0.09。
- 沙箱分析的 USD 0.000268 只对应它收到的单个任务、分析前的账本，不是全轮花费，
  也不包含分析调用自身。工作台合计与本报告需分别看待。

## 真实使用暴露的问题与修复

1. 首次提取发生 HTTP 504，原任务暂停。非流式原请求的相同幂等键随后获得
   `Otari-Idempotent-Replayed: true`，费用 USD 0.001852；模型的 reasoning 耗尽
   1800 输出 token，最终结构化正文为空。现在按角色配置 reasoning_effort=none，
   并拒绝 finish_reason=length 的不完整结果，保留实际计费元数据。
2. 原通用提取提示把明确的虚构项目偏好当成缺少外部验证而丢弃。工作台采用独立提示，
   区分“用户声明的约定”和“独立核实的技术事实”，真实重新提取并落库通过。
3. 第一次网页回答删去了 HTML 排版换行，被精确原句校验拒绝。抓取器现在合并普通
   段落中的排版空白，保留段落分隔和 pre 代码缩进；新内容保存为 r2，旧 r1 不覆盖。
   精确引文校验仍保持严格。
4. 当前托管 Chat Completions 返回了 web_search 记录，但本轮代码/MCP 调用缺少相应
   顶层记录。没有将模型自述计为执行证明。改用 Messages 原生工具结果：
   MCP 带 `mcp-client-2025-11-20` beta；代码声明采用 `code_execution_20250522`，
   取得实际工具结果后再标 verified。网页搜索与结构化提取/综合继续使用 Chat Completions。
5. **流式请求不能沿用非流式幂等缓存的假设。** 一次重复流式请求没有 replay 标记且
   再次计费 USD 0.011151。因此流式工具请求在派发后异常或进程中断时要求人工核对，
   禁止自动再次派发；预算等明确派发前拒绝仍可修复后继续。
6. 回看回答发现模型曾把规范性的“未知状态应保留”套到当前费用。综合步骤现在接收
   独立的 `run_usage`，明确仅包含综合前已完成调用；新任务
   `f08a9220f24043a88c43454e53f7b2db` 能说明当时数组为空，随后沙箱实际汇总
   USD 0.000286、1712 输入 / 382 输出 tokens。但措辞仍有过强推论，不能把提示修改
   当成完整语义保证。账本和执行详情为实际运行依据。
7. Messages 的输入用量须合计 input、cache read、cache creation 三项，已在消费契约中
   修正。此次较早的 Messages 历史记录未保留完整缓存拆分，不能追溯为完整输入总量；
   报告保留原记录，不补造计数。该限制不影响实际回报的美元费用。
   依据：[Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)。

新行为的最小契约依次由 RED 到 GREEN：reasoning/output 限制 4 项、HTML 证据 3 项、
原生工具结果、流式未知结果恢复及运行账本上下文 6 项。共 13 项分阶段通过，未运行旧回归套件。
真实提示评估也保留了上述失败基线与成功任务，不能从有限次数推断稳定成功率。

## 清理及尚未覆盖

临时隧道与独立 MCP 进程已停止；Otari 中的演示服务器已禁用且临时令牌已清除。
公开期间只提供仓库原有 `docs/demo/vault/refund-policy.md`，三项只读工具；
本机个人库与工作台 API 未发布。当前本机配置清空活动 MCP server IDs，历史证据仍可浏览。
再次在线演示 MCP 需要重新准备临时入口并获得对应授权。

引用校验证明原文存在，不证明每句话推理正确。MCP 采用远程引用的一次回答以“是”开头，
随后明确说“不含真实记录”，前缀存在语义不一致；另一次回答正确引用了本机同文来源，
但没有遵从“只引用 remote/”的要求。这些质量问题保留为观察，未伪装成全部通过。
代码 stdout 是服务端返回的展示文本，未将其当成严格的应用 JSON 数据接口。

尚缺真实供应商回退证据、录制前的一次完整连贯演示，以及参赛者本人的有声视频。
迟报名资格、截止时区与最终提交仍需按主办方要求处理。本轮未购买额度或发送报名/提交邮件。

接口依据：[Otari tools](https://github.com/mozilla-ai/otari/blob/main/docs/tools.md)、
[MCP](https://github.com/mozilla-ai/otari/blob/main/docs/mcp.md)、
[API reference](https://github.com/mozilla-ai/otari/blob/main/docs/api-reference.md)。
临时入口采用官方 [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)，
仅供这次已授权验收使用，未作为持续部署。
