## Standardized Log Format

All log entries use grep-friendly format on a single line:

```
[ISO-timestamp] [SESSION-N] <TYPE> [task-id]? [category]? message
```

`[task-id]` and `[category]` are included when applicable (task-scoped entries). Session-level entries (`INIT`, `LOCK`, `STATS`) omit them.

Types: `INIT`, `Starting`, `Completed`, `ERROR`, `CHECKPOINT`, `ROLLBACK`, `RECOVERY`, `STATS`, `LOCK`, `WARN`

Error categories: `ENV_SETUP`, `CONFIG`, `TASK_EXEC`, `TEST_FAIL`, `TIMEOUT`, `DEPENDENCY`, `SESSION_TIMEOUT`

Filtering:
```bash
grep "ERROR" harness-progress.txt                    # All errors
grep "ERROR" harness-progress.txt | grep "TASK_EXEC" # Execution errors only
grep "SESSION-3" harness-progress.txt                # All session 3 activity
grep "STATS" harness-progress.txt                    # All session summaries
grep "CHECKPOINT" harness-progress.txt               # All checkpoints
grep "RECOVERY" harness-progress.txt                 # All recovery actions
```
