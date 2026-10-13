## Context Window Recovery Protocol

When a new session starts and finds a task with `status: "in_progress"`:

- Exclusive mode: treat this as an interrupted previous session and run the Recovery Protocol below.
- Concurrent mode: only recover a task if either (a) `claimed_by` matches this worker, or (b) `lease_expires_at` is in the past (stale lease). Otherwise, treat it as owned by another worker and do not modify it.

1. **Check git state**:
   ```bash
   git diff --stat          # Uncommitted changes?
   git log --oneline -5     # Recent commits since task started?
   git stash list           # Any stashed work?
   ```
2. **Check checkpoints**: Read the task's `checkpoints` array to determine last completed step
3. **Decision matrix** (verify recent commits belong to this task by checking commit messages for the task-id):

| Uncommitted? | Recent task commits? | Checkpoints? | Action |
|---|---|---|---|
| No | No | None | Mark `failed` with `[SESSION_TIMEOUT] No progress detected`, increment attempts |
| No | No | Some | Verify file state matches checkpoint claims. If files reflect checkpoint progress, resume from last step. If not, mark `failed` — work was lost |
| No | Yes | Any | Run `validation.command`. If passes → mark `completed`. If fails → `git reset --hard <started_at_commit>`, mark `failed` |
| Yes | No | Any | Run validation WITH uncommitted changes present. If passes → commit, mark `completed`. If fails → `git reset --hard <started_at_commit>` + `git clean -fd`, mark `failed` |
| Yes | Yes | Any | Commit uncommitted changes, run `validation.command`. If passes → mark `completed`. If fails → `git reset --hard <started_at_commit>` + `git clean -fd`, mark `failed` |

4. **Log recovery**: `[timestamp] [SESSION-N] RECOVERY [task-id] action="<action taken>" reason="<reason>"`
