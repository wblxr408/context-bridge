## Concurrency Control

Before modifying `harness-tasks.json`, acquire an exclusive lock using portable `mkdir` (atomic on all POSIX systems, works on both macOS and Linux):

```bash
# Acquire lock (fail fast if another agent is running)
# Lock key must be stable even if invoked from a subdirectory.
ROOT="$PWD"
SEARCH="$PWD"
while [ "$SEARCH" != "/" ] && [ ! -f "$SEARCH/harness-tasks.json" ]; do
  SEARCH="$(dirname "$SEARCH")"
done
if [ -f "$SEARCH/harness-tasks.json" ]; then
  ROOT="$SEARCH"
fi

PWD_HASH="$(
  printf '%s' "$ROOT" |
    (shasum -a 256 2>/dev/null || sha256sum 2>/dev/null) |
    awk '{print $1}' |
    cut -c1-16
)"
LOCKDIR="/tmp/harness-${PWD_HASH:-unknown}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  # Check if lock holder is still alive
  LOCK_PID=$(cat "$LOCKDIR/pid" 2>/dev/null)
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    echo "ERROR: Another harness session is active (pid=$LOCK_PID)"; exit 1
  fi
  # Stale lock — atomically reclaim via mv to avoid TOCTOU race
  STALE="$LOCKDIR.stale.$$"
  if mv "$LOCKDIR" "$STALE" 2>/dev/null; then
    rm -rf "$STALE"
    mkdir "$LOCKDIR" || { echo "ERROR: Lock contention"; exit 1; }
    echo "WARN: Removed stale lock${LOCK_PID:+ from pid=$LOCK_PID}"
  else
    echo "ERROR: Another agent reclaimed the lock"; exit 1
  fi
fi
echo "$$" > "$LOCKDIR/pid"
trap 'rm -rf "$LOCKDIR"' EXIT
```

Log lock acquisition: `[timestamp] [SESSION-N] LOCK acquired (pid=<PID>)`
Log lock release: `[timestamp] [SESSION-N] LOCK released`

Modes:

- **Exclusive (default)**: hold the lock for the entire session (the `trap EXIT` handler releases it automatically). Any second session in the same state root fails fast.
- **Concurrent (opt-in via `session_config.concurrency_mode: "concurrent"`)**: treat this as a **state transaction lock**. Hold it only while reading/modifying/writing `harness-tasks.json` (including `.bak`/`.tmp`) and appending to `harness-progress.txt`. Release it immediately before doing real work.

Concurrent mode invariants:

- All workers MUST point at the same state root (the directory that contains `harness-tasks.json`). If you are using separate worktrees/clones, pin it explicitly (e.g., `HARNESS_STATE_ROOT=/abs/path/to/state-root`).
- Task selection is advisory; the real gate is **atomic claim** under the lock: set `status="in_progress"`, set `claimed_by` (stable worker id, e.g., `HARNESS_WORKER_ID`), set `lease_expires_at`. If claim fails (already `in_progress` with a valid lease), pick another eligible task and retry.
- Never run two workers in the same git working directory. Use separate worktrees/clones. Otherwise rollback (`git reset --hard` / `git clean -fd`) will destroy other workers.
