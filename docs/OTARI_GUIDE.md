# Bridge · Otari 参赛工作台

这个分支实现一个有出处的个人记忆研究流程：对话提取 → 当前记忆检索 →
官方资料核对 → 引用回答 → 调用账本与代码分析 → 中断后继续。
它使用已有 Python、Markdown 记忆库和 SQLite，不安装第二个长期记忆服务。

**当前状态：代码和本地行为验收已完成；本机凭据已配置并成功读取托管模型目录。
真实模型推理、工具、路由和花费限额验收仍未完成。当前不能声称已达到某个比赛分数或已取得奖金资格。**

工作台已按用户指定的 Maple Ridge House 适配为暖奶油色浮雕界面，采用 Poppins /
Roboto Mono、卡片任务网格和右侧实际状态仪表。映射与验收见 [设计说明](OTARI_DESIGN.md)。

比赛分支：[`codex/otari-devs-wilding`](https://github.com/wblxr408/context-bridge/tree/codex/otari-devs-wilding)。
首次引入 Otari 的提交：[`2177c03`](https://github.com/wblxr408/context-bridge/commit/2177c03)。
[完整 TODO 与实际验收记录](OTARI_TODO.md) · [演示与提交材料](OTARI_SUBMISSION.md)。

## 启动独立演示

Python 3.12；命令从仓库根目录运行。以下新建独立演示目录，不修改已安装的个人监听器。
原项目依赖体积较大，复用现有 Basic Memory Python 环境也可。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item docs/otari-config.example.json config.local.json
New-Item -ItemType Directory -Force local-vault | Out-Null
Copy-Item docs/demo/vault/*.md local-vault/
```

编辑 `config.local.json`：

- `vault` 指向演示 Markdown 库；状态默认写入 `local-state/otari.sqlite`。
- `otari.models.extract` 使用一个实际可用的开放权重模型。
- `otari.models.reflect` 使用另一个开放权重模型，承担证据综合职责。
- `research`、`analysis` 可复用其中一个支持工具的模型或 Otari 路由策略。
  示例保留待填值；必须从自己工作区的当前模型目录选择，不能把待填值直接发给网关。
- `base_url` 默认 `https://otari.ai/api/v1`；密钥只通过环境变量提供。
- `research.official_domains` 是精确域名允许列表。网页检索由 Otari 执行；
  只有允许列表中的公开 HTTPS 文本会由应用独立取回并保存为可核对快照。
  这个独立取回步骤本身不算一次 Otari web-fetch 使用。
- `max_calls_per_day/hour` 与 `max_tokens_per_day` 是共享的本地模型预算。
  **比赛的 Otari 花费限额必须另在 Otari 工作区配置并实际触发验证。**

在启动进程的安全环境中设置 `OTARI_API_KEY`。不要把密钥写入配置、命令示例、
截图、聊天或仓库；本指南不提供带真实值的命令。然后：

```powershell
.\.venv\Scripts\python.exe app/otari_app.py workbench --config config.local.json --port 8765
```

打开日志显示的本机地址。此主机上部分固定端口返回 Windows 10013；可改用
`--port 0`，让系统分配端口，再打开日志里的实际地址。

不提供密钥时仍可浏览已保存任务；需要模型的任务会保存状态并明确暂停。
工作台显示“凭据已配置”只表示环境变量存在，不能证明认证或托管请求成功。

## 使用与恢复

“填入示例”只填充输入，不会直接发送请求。点击“开始研究”后，任务保留问题、
对话、原始证据、准备好的模型请求和工具返回结果。点击回答引用即可回读原句。
“执行过程”展示网关实际返回的工具记录；未返回记录时保留未验证状态。

示例输入见 [conversations.json](demo/conversations.json)。先演示对话提取和最新
修正，再核对 Python 官方 `lru_cache` 文档，最后运行代码分析和恢复流程。
新任务会重新读取来源；继续旧任务则保留原快照，不偷偷替换已发送的证据。

预算、认证、限流和不确定的网络结果会暂停。修复当前配置/预算后点“继续任务”。
一个任务的模型、网关地址和已准备请求被冻结；更换模型/网关或刷新来源需要新建任务。
进程异常退出后，工作租约最长 15 分钟，过期后允许继续；关闭网页不会取消后台执行。
同一请求用稳定的 `Idempotency-Key`，本地操作与预算预留在同一事务中绑定。
超过 23 小时的未确认请求不会再次发送，必须先核对 Otari 活动记录。
网关的实际幂等缓存保留期和重放行为仍需在托管验收中确认；不能承诺无限期只计费一次。

来源不足时不调用综合模型。无效结构或缺少精确支持原句的结果不会成为回答。
精确原句校验只证明引用存在，不能自动证明每个推论都成立；演示者应检查回答语义。
网页快照记录的是有界提取文本，非完整网页归档，最多四个来源，每个最多 60,000 字符。
应用不跟随重定向；失败或不允许的来源会列出警告。

命令行也能运行与继续：

```powershell
.\.venv\Scripts\python.exe app/otari_app.py run --config config.local.json --query '退款重试的幂等约定是什么？'
.\.venv\Scripts\python.exe app/otari_app.py run --config config.local.json --resume YOUR_TASK_ID
```

## 只读 HTTP MCP

MCP 使用独立端口和独立应用；公开端点不会顺带暴露工作台 API。
`remote_mcp.scope` 必须明确，`permalinks` 只列允许公开给 Otari 的来源。
笔记同时满足精确 scope 和 permalink 才能被读取；网页快照须列出具体版本 citation。
默认为演示笔记 `main/demo/refund-policy`。不应将整个个人库加入发布列表。

在运行环境安全设置独立的 `BRIDGE_MCP_TOKEN`，至少 12 字符。它与 Otari 密钥不同。

```powershell
.\.venv\Scripts\python.exe app/otari_app.py mcp --config config.local.json --port 8766
```

提供三项只读工具：`search_memory`、`read_source`、`source_revision`。
支持 Streamable HTTP `/mcp`，要求 `Authorization: Bearer …`；无写入、反思或刷新工具。
`read_source` 可携带 revision，来源变化时拒绝旧 revision，避免悄悄替换证据。

Otari 托管服务无法访问本机地址。后续须选择经授权的 HTTPS 反向代理或受控部署，
仅转发 MCP 应用，配置证书和 `allowed_hosts` 精确主机名，保留 bearer 认证。
在 Otari 添加服务器并只允许上述三项工具，将保存的服务器 ID 写入
`research.mcp_server_ids`，然后从工作台实际读取。当前未创建外网隧道或部署。
应用只把已完成 `read_source` 的实际 JSON 原文纳入回答，搜索摘要或模型声称不算。

## 评分证据与交付边界

| 目标 | 应用中的证据 | 真实托管状态 |
| --- | --- | --- |
| 至少一个开放权重模型 20；不同用途的第二个再 10 | 提取与综合角色、实际模型名称和请求编号 | 待选型、真实调用与模型许可证核对 |
| 路由与回退 10 | 网关返回的实际模型、fallback、attempt count | 待配置路由并取得真实回退记录 |
| MCP 10 | 远程搜索/原文/版本调用及原文参与回答 | 本地协议通过；外部 HTTPS 与 Otari 调用待做 |
| Web 10 | Otari 完成的搜索记录、官方来源快照与引用 | 本地契约通过；工作区开关与真实搜索待做 |
| 代码执行 10 | 实际 code/stdout/exit_code 与账本分析 | 本地契约通过；真实沙箱调用待做 |
| 预算 10 | Otari 预算拒绝及保存任务后继续 | 本地预算通过；网关花费限额拒绝待做 |
| 多模型分工 10 | 不同角色实际模型调用与用途 | 待真实调用 |
| 项目与演示 10 | 可操作工作台 + 参赛者亲自录制的演示 | 本地界面通过；真人视频待录 |

Otari 功能类别最多 60 分；上表是理论覆盖，不是已得分。
护栏与按用户预算不在本分支的六项主目标中。启用开关、本地预算或本地 MCP
都不能独自证明相应 Otari 功能已在应用中使用。

本轮按阶段只运行新增功能契约，没有重跑旧回归套件；未运行安装器或替换个人服务。
完整真实托管验收待密钥配置后进行，记录每项的任务 ID、模型、请求 ID、实际工具结果、
费用/未知值及预期行为，不能使用合成记录代替。不要为了制造回退破坏实际供应商配置。

## 依赖与来源

官方接口与工具：[API reference](https://github.com/mozilla-ai/otari/blob/main/docs/api-reference.md)、
[tools](https://github.com/mozilla-ai/otari/blob/main/docs/tools.md)、
[MCP](https://github.com/mozilla-ai/otari/blob/main/docs/mcp.md)。
官方 MCP Python SDK 2.2 提供 HTTP 协议；Starlette/Uvicorn 提供本机服务。
Fraunces 字体以 SIL OFL 分发，见 [字体许可证](FRAUNCES-OFL.txt)。
项目整体许可证仍沿用仓库原状态，未擅自替作者选择。
