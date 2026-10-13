---
name: context-bridge
description: Checkpoint, resume, and hand off long tasks using verified local bundles, Basic Memory cursors, and persistent task state with safe ownership.
metadata:
  version: "fusion-2026-10-12"
---

# Context Bridge — unified task continuity

Basic Memory checkpoint 原件的历史摘要、隔离、恢复和到期删除，读取 [checkpoint 生命周期](references/checkpoint-lifecycle.md)。本分支不调用 local bundle retention.py。

Read [the execution contract](references/fusion-policy.md). Preserve the original objective, latest corrections, authorization, constraints, completion evidence, outstanding work, and one next action. Git state anchors code; it does not replace task state. Short tasks continue directly; assess context pressure only at a new milestone, observed loss, impending compaction, or a large new work block. Unknown usage stays unknown.

| Current need | Read next |
|---|---|
| Decide whether to checkpoint or migrate | [decision](references/decision.md) |
| Save a reproducible local handoff bundle | [handoff](references/handoff.md) |
| Resume an exact local bundle, reconcile requirements/live state, or accept ownership | [resume](references/resume.md) |
| Save an immutable Basic Memory checkpoint | [memory save](references/memory-save.md), then [save module](modules/memory-save/PLAYBOOK.md) |
| Resume an exact Basic Memory identifier, discover a topic, or orient to repository state | [memory resume](references/memory-resume.md), then [resume module](modules/memory-resume/PLAYBOOK.md) |
| Persistent task queue, concurrent leases, task selection, environment/failure recovery | [task state](references/task-state.md), then [task-state module](modules/task-state/PLAYBOOK.md) |
| Retention, locks, receipt validation, integration, or cross-Codex/Claude host use | Select [retention](references/retention.md), [integration](references/integration.md), or [hosts](references/hosts.md) |

A local bundle and a memory note are complementary: use one for the actual need, and combine them with an exact pointer when both are necessary. Do not save two independent copies of the same large state by default. A supplied exact identifier is never silently replaced by a newer checkpoint. Compare live files, branch/SHA, requirements, and ownership before continuing.

Never overwrite immutable checkpoints, delete another task's work, or use `git reset --hard` as automatic failure recovery. A failed validation is diagnosed and scoped; absent checks are named rather than passed. Native task goals and human deadlines govern continuation; no infinite loop or automatic recurring schedule. Only a user request creates a new chat or automation. Basic Memory tools, setup, writing standard, and durable engineering recall remain available.

Compatibility intents `$bm-checkpoint`, `$bm-orient`, and `/harness` map to these routes. Report the exact returned checkpoint cursor and a `$context-bridge resume <cursor>` command after saving.

For development continuity, retain the intended behavior and actual TDD/regression evidence under ../dev/references/testing.md. File hashes or smoke probes cannot serve as development acceptance. ECC strategic-compact/ck/unified-memory intents route here or engineering-memory; do not register another default vault or observer.

Current development continuity does not create or compare hashes. Preserve exact identifiers, requirement versions, semantic evidence and ownership; use the current handoff/resume guides. Historical bundle/retention scripts that require checksum validation are not the default route. Source provenance can identify a Git revision without treating revision identity as functional proof.
