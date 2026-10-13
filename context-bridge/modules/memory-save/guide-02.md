## Gather

Read `~/.codex/basic-memory.json`, then the nearest project
`.codex/basic-memory.json`; project keys override user keys:

- `primaryProject`, default omitted
- `captureFolder`, default `codex/<git top-level directory name>`
- `placementConventions`, optional
- `sessionProfile`, default `general`
- `repository`, required when `sessionProfile` is `coding`

Apply the `bm-writing` skill before drafting the note.

Gather repo evidence:

- the original objective that started the thread and why it mattered
- the latest user intent, including corrections or scope changes that supersede
  the original objective
- the approach taken and why it solves the problem
- the current system state and practical impact
- tradeoffs, sharp edges, useful simplifications, and intentionally parked work
- `git status --short`
- current branch
- repository root and current working directory
- current Git SHA
- current pull request number, title, URL, state, base, and head when one exists
- changed files you touched
- tests or checks actually run
- failures or skipped checks
- decisions made in this thread
- unresolved blockers
- next action
- current username, hostname, and timestamp
- host-provided `session_id`, `agent`, `codex_turn_id`, `trigger`, and `model`
  values from the checkpoint request, when present

Use direct, read-only evidence for repository and pull-request state. Do not
claim a test passed unless you ran it or the user supplied the result.
Treat host-provided session metadata as opaque identity data. Preserve exact
non-empty values; never infer or rewrite them. For older requests supplying only
`codex_session_id`, use that exact value as `session_id` with `agent: codex`.
Do not emit the legacy field on new checkpoints.
