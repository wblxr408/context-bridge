## Error Handling & Recovery Strategies

Each error category has a default recovery strategy:

| Category | Default Recovery | Agent Action |
|----------|-----------------|--------------|
| `ENV_SETUP` | Re-run init, then STOP if still failing | Run `harness-init.sh` again immediately. If fails twice, log and stop — environment is broken |
| `CONFIG` | STOP (requires human fix) | Log the config error precisely (file + field), then STOP. Do not guess or auto-mutate task metadata |
| `TASK_EXEC` | Rollback via `git reset --hard <started_at_commit>`, retry | Verify `started_at_commit` exists (`git cat-file -t <hash>`). If missing, mark failed at max_attempts. Otherwise reset, run `on_failure.cleanup` if defined, retry if attempts < max_attempts |
| `TEST_FAIL` | Rollback via `git reset --hard <started_at_commit>`, retry | Reset to `started_at_commit`, analyze test output to identify fix, retry with targeted changes |
| `TIMEOUT` | Kill process, execute cleanup, retry | Wrap validation with `timeout <seconds> <command>`. On timeout, run `on_failure.cleanup`, retry (consider splitting task if repeated) |
| `DEPENDENCY` | Skip task, mark blocked | Log which dependency failed, mark task as `failed` with dependency reason |
| `SESSION_TIMEOUT` | Use Context Window Recovery Protocol | New session assesses partial progress via Recovery Protocol — may result in completion or failure depending on validation |

**JSON corruption**: If `harness-tasks.json` cannot be parsed, check for `harness-tasks.json.bak` (written before each modification). If backup exists and is valid, restore from it. If no valid backup, log `ERROR [ENV_SETUP] harness-tasks.json corrupted and unrecoverable` and STOP — task metadata (validation commands, dependencies, cleanup) cannot be reconstructed from logs alone.

**Backup protocol**: Before every write to `harness-tasks.json`, copy the current file to `harness-tasks.json.bak`. Write updates atomically: write JSON to `harness-tasks.json.tmp` then `mv` it into place (readers should never see a partial file).
