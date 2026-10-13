## Status Command (`/harness status`)

Read `harness-tasks.json` and `harness-progress.txt`, then display:

1. Task summary: count by status (completed, failed, pending, blocked). `blocked` = pending tasks whose `depends_on` includes a permanently failed task (computed, not a stored status).
2. Per-task one-liner: `[status] task-id: title (attempts/max_attempts)`
3. Last 5 lines from `harness-progress.txt`
4. Session count and last session timestamp

Does NOT acquire the lock (read-only operation).
