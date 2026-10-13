## Infinite Loop Protocol

### Session Start (Execute Every Time)

1. **Read state**: Read last 200 lines of `harness-progress.txt` + full `harness-tasks.json`. If JSON is unparseable, see JSON corruption recovery in Error Handling.
2. **Read git**: Run `git log --oneline -20` and `git diff --stat` to detect uncommitted work
3. **Acquire lock** (mode-dependent): Exclusive mode fails if another session is active. Concurrent mode uses the lock only for state transactions.
4. **Recover interrupted tasks** (see Context Window Recovery below)
5. **Health check**: Run `harness-init.sh` if it exists
6. **Track session**: Increment `session_count` in JSON. Check `session_count` against `max_sessions` — if reached, log STATS and STOP. Initialize per-session task counter to 0.
7. **Pick next task** using Task Selection Algorithm below

### Task Selection Algorithm

Before selecting, run dependency validation:

1. **Cycle detection**: For each non-completed task, walk `depends_on` transitively. If any task appears in its own chain, mark it `failed` with `[DEPENDENCY] Circular dependency detected: task-A -> task-B -> task-A`. Self-references (`depends_on` includes own id) are also cycles.
2. **Blocked propagation**: If a task's `depends_on` includes a task that is `failed` and will never be retried (either `attempts >= max_attempts` OR its `error_log` contains a `[DEPENDENCY]` entry), mark the blocked task as `failed` with `[DEPENDENCY] Blocked by failed task-XXX`. Repeat until no more tasks can be propagated.

Then pick the next task in this priority order:

1. Tasks with `status: "pending"` where ALL `depends_on` tasks are `completed` — sorted by `priority` (P0 > P1 > P2), then by `id` (lowest first)
2. Tasks with `status: "failed"` where `attempts < max_attempts` and ALL `depends_on` are `completed` — sorted by priority, then oldest failure first
3. If no eligible tasks remain → log final STATS → STOP

### Task Execution Cycle

For each task, execute this exact sequence:

1. **Claim** (atomic, under lock): Record `started_at_commit` = current HEAD hash. Set status to `in_progress`, set `claimed_by`, set `lease_expires_at`, log `Starting [<task-id>] <title> (base=<hash>)`. If the task is already claimed (`in_progress` with a valid lease), pick another eligible task and retry.
2. **Execute with checkpoints**: Perform the work. After each significant step, log:
   ```
   [timestamp] [SESSION-N] CHECKPOINT [task-id] step=M/N "description of what was done"
   ```
   Also append to the task's `checkpoints` array: `{ "step": M, "total": N, "description": "...", "timestamp": "ISO" }`. In concurrent mode, renew the lease at each checkpoint (push `lease_expires_at` forward).
3. **Validate**: Run the task's `validation.command` with a timeout wrapper (prefer `timeout`; on macOS use `gtimeout` from coreutils). If `validation.command` is empty/null, log `ERROR [<task-id>] [CONFIG] Missing validation.command` and STOP — do not declare completion without an objective check. Before running, verify the command exists (e.g., `command -v <binary>`) — if missing, treat as `ENV_SETUP` error.
   - Command exits 0 → PASS
   - Command exits non-zero → FAIL
   - Command exceeds timeout → TIMEOUT
4. **Record outcome**:
   - **Success**: status=`completed`, set `completed_at`, log `Completed [<task-id>] (commit <hash>)`, git commit
   - **Failure**: increment `attempts`, append error to `error_log`. Verify `started_at_commit` exists via `git cat-file -t <hash>` — if missing, mark failed at max_attempts. Otherwise execute `git reset --hard <started_at_commit>` and `git clean -fd` to rollback ALL commits and remove untracked files. Execute `on_failure.cleanup` if defined. Log `ERROR [<task-id>] [<category>] <message>`. Set status=`failed` (Task Selection Algorithm pass 2 handles retries when attempts < max_attempts)
5. **Track**: Increment per-session task counter. If `max_tasks_per_session` reached, log STATS and STOP.
6. **Continue**: Immediately pick next task (zero idle time)

### Stopping Conditions

- All tasks `completed`
- All remaining tasks `failed` at max_attempts or blocked by failed dependencies
- `session_config.max_tasks_per_session` reached for this session
- `session_config.max_sessions` reached across all sessions
- User interrupts
