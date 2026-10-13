## Activation Marker

Hooks only take effect when `.harness-active` marker file exists in the harness root (same directory as `harness-tasks.json`).

- `/harness init` and `/harness run` MUST create this marker: `touch <project-path>/.harness-active`
- When all tasks complete (no pending/in_progress/retryable left), remove it: `rm <project-path>/.harness-active`
- Without this marker, all hooks are no-ops — they exit 0 immediately
