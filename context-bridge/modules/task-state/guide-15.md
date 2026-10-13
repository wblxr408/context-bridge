## Add Command (`/harness add`)

Append a new task to `harness-tasks.json` with auto-incremented id (`task-NNN`), status `pending`, default `max_attempts: 3`, empty `depends_on`, and no validation command (required before the task can be completed). Prompt user for optional fields: `priority`, `depends_on`, `validation.command`, `timeout_seconds`. Requires lock acquisition (modifies JSON).
