---
name: engineering-memory
description: Retrieve personal engineering history and capture reusable lessons in Basic Memory at task decisions, verification results, corrections, and handoffs.
---

# Engineering memory

Use the existing `basic-memory` MCP service, project `main`. The confirmed local vault is `C:/Users/wblxr/basic-memory`. The unrelated `memory` server is not this knowledge base. This skill guides the agent; Basic Memory provides storage, indexing, and tools. Plugin SessionStart/PreCompact hooks supply lifecycle context, not autonomous evaluation of every conversation event.

Load only the relevant procedure, and reuse it within the task:

- **Recall:** Before relying on personal engineering history or making a consequential technical decision, read [retrieval](references/retrieval.md). Reuse applicable notes already read; changed scope or evidence can trigger a new search.
- **Capture:** When verification, a clarified failure, a decision change, user correction, milestone, or handoff yields a potentially reusable lesson, read [capture](references/capture.md) before deciding whether and how to save. At task completion, check for formed conclusions not yet captured. The background listener may reconcile changed files periodically; do not repeatedly re-evaluate unchanged conversations.
- **Background listener:** For multi-client monitoring, status, source configuration, budgets, or stop/start, read [listener operations](references/listener.md). The user has authorized Codex and Claude Code sources plus periodic incremental reconciliation.
- **Connection failure:** If native tools are missing or cannot connect, read [connection fallback](references/connection.md). Its local helper uses the same MCP service and supports read-only retrieval.

Do not load all references on every task. Generic explanations and edits with no personal-history dependency can skip recall. Events with no new or changed knowledge need no capture. Routine retrieval stays quiet; explain material conflicts, failures, or the effect of prior knowledge. After a successful save, briefly state what was retained.

The user has authorized routine local capture under this workflow. Preserve evidence boundaries and deduplicate before saving; verify saved content. Store durable facts in Basic Memory, execution guidance in this skill, and only the short trigger in global AGENTS.md.

For development-learning and instinct promotion, read ../dev/references/learning.md. Keep project-scoped evidence, uncertainty and applicability in Basic Memory main. Use the existing listener; do not start ECC continuous-learning as a second observer.

- **增强召回、事实观察、知识页、反思、自动注入和历史补录：** 读 [增强记忆](references/enhanced-memory.md)。复用 main 与既有监听器。
