## Session Statistics

At session end, update `harness-tasks.json`: set `last_session` to current timestamp. (Do NOT increment `session_count` here — it is incremented at Session Start.) Then append:

```
[timestamp] [SESSION-N] STATS tasks_total=10 completed=7 failed=1 pending=2 blocked=0 attempts_total=12 checkpoints=23
```

`blocked` is computed at stats time: count of pending tasks whose `depends_on` includes a permanently failed task. It is not a stored status value.
