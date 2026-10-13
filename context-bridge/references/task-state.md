# task state

Retain harness's persistent tasks, dependencies, validation commands, progress log, session statistics, environment setup, task selection, leases/locks, and recovery classification. Use only when multiple resumable tasks or concurrent owners need state. Simple handoffs need the bridge/memory routes instead.

Claim a task under a lock, retain the start anchor, checkpoint after meaningful progress, renew a lease only while actively working, and validate the task's behavior before declaring completion. Recover expired ownership by checking actual files and commits. Diagnose partial progress and resume the useful work; automatic git reset --hard and arbitrary rollback are prohibited. Empty validation evidence cannot be labeled a pass.

Preserve task-specific stop conditions, human goals/deadlines/budgets, and explicit pause. Do not start an infinite autonomous loop, recurring monitor, or a new chat without the user's request. Native task goal continuation is governed by the host; source harness marker is a compatibility artifact, not permission to disregard user steering.
