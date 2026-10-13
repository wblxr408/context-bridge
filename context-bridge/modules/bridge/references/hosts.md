# 宿主适配：仅跨工具使用或运行环境排错时读取

核心 checkpoint、账本、任务版本、回执、协作锁和保留策略均为本地文件协议，不依赖 Codex 专属 API。Codex 与 Claude Code 使用同一套 Python 脚本；切换工具不改变包版本、要求 ID、scope 或写入所有权。

## 本机发现与调用

| 宿主 | 个人技能路径 | 显式调用 |
|---|---|---|
| Codex | C:/Users/wblxr/.codex/skills/context-bridge | $context-bridge |
| Claude Code | C:/Users/wblxr/.claude/skills/context-bridge | /context-bridge |

Claude Code 的目录通过 Windows junction 指向 Codex 技能实体目录，所有脚本和参考文件共享。维护只修改实体目录，不能删除 junction 的目标；安装到其他机器时可在该机器各自的个人 skills 目录部署同一份包。此配置针对本机 Claude Code，不代表已安装到 claude.ai、Cowork 或远程容器。

两端全局指令只保存简短事件触发语句，不内嵌本技能。主入口只选当前分支；不得因为兼容两端就预读所有文件。Codex 的 agents/openai.yaml 不作为 Claude 的运行前提；SKILL.md 使用通用 name/description。

## 脚本执行

Python 需要 3.9+，脚本仅用标准库。<skill> 替换为当前读取的技能根目录；必须使用绝对包路径、工作目录和 claim 路径。遵循宿主现有执行权限，不修改权限或跳过确认来“兼容”。

本机已验证解释器：C:/Users/wblxr/anaconda3/python.exe。PowerShell 示例：

`& 'C:/Users/wblxr/anaconda3/python.exe' 'C:/Users/wblxr/.claude/skills/context-bridge/scripts/requirements.py' brief '<bundle>' --scope '<scope>'`

Claude 使用其他 shell 时按该 shell 的引用规则调用同一解释器；不能把 PowerShell 的 & 语法复制到 Bash。仅遇到解释器或路径问题才探测环境，不在每次调用技能时重复发现。

## 对话与工具能力

Codex 仅在当前环境实际暴露并允许 create_thread 时使用它。Claude Code 不假定存在该工具；无可用创建工具时，写好恢复提示，由用户在新 Claude Code 会话中调用 /context-bridge，或在 Codex 中调用 $context-bridge。不要用 --resume、fork 或复制完整聊天历史宣称已减少上下文。

跨端交接仍要求源端停写、task_id/snapshot_id 一致、接收回执和 claim 校验。不同宿主的线程/工具会话 ID 只作线索；不要假定另一端可以读源端聊天、重连终端或继承权限。无法确认完整历史时明确披露实际覆盖范围。

恢复提示范式：使用 context-bridge 恢复分支；包=<绝对路径>，snapshot_id=<task-id/revision-id>，workspace=<绝对路径>，scope=<工作块>，claim=<本地绝对路径>。先校验当前指令、要求覆盖、文件现场和所有权，再继续已授权任务。

参考：[Claude Code Skills 官方文档](https://code.claude.com/docs/en/skills)，2026-09-27 核对个人路径、/skill-name 调用、目录链接和按需加载机制。
