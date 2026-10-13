# Background listener operations

Installed service: `C:/Users/wblxr/.codex/services/engineering-memory`. Program files are in `app/`; `config.json` lists sources, budget and cadence. It uses the same Basic Memory main vault. Windows task `EngineeringMemoryListener` starts at user login and retries startup every five minutes; file notifications are primary, five-minute incremental reconciliation covers missed changes. A singleton lock prevents duplicate workers.

Supported sources: Codex `.codex/sessions`, `.codex/archived_sessions`, and Claude Code `.claude/projects`, recursively. Additional local directories must use one of these JSONL formats and be added to `sources`; restart after config changes. First install baselines old files instead of backfilling history. Sources outside this user's local files are not automatically discovered.

Use PowerShell `& 'C:/Users/wblxr/.codex/services/engineering-memory/app/control.ps1' status`, `stop`, or `start`. Stop disables automatic restart and lets an in-flight judgment finish; wait for the task to stop before starting again. `status.json` contains timestamped heartbeat, sources, job counts and rolling usage. `listener.log` has rotating diagnostics; SQLite `state.sqlite` persists offsets, queue, results and calls. A stale heartbeat is not proof of a live listener.

Local filtering and polling consume no model tokens. A candidate uses the installed Codex CLI, current configured model, existing login, and an ephemeral structured-output run. Claude excerpts also go to that configured Codex model. Default limits: two calls/hour, eight/day and 60,000 rolling tokens with 12,000 reserved before each call. Reservation is a scheduling threshold, not a hard API output limit. A measured synthetic candidate cost 7,884 input plus 123 output tokens; do not promise hundreds of tokens per call.

Only completed-turn user/final text is selected in full and subjected to basic credential redaction. Thinking, full tool logs and images are excluded. Exact source quotations are checked. `40-Automatic` contains automatic captures, with technical claims marked experimental and explicit user preferences accepted. Existing human notes are not overwritten; related new evidence gets a separate linked note for later verified consolidation. Conversation evidence is not independent reproduction of an experiment.

Job meanings: filtered = local rejection; queued/retry = waiting; skipped = model rejected capture; ready_to_save = judgment persisted; awaiting_index = locally saved, awaiting Basic Memory read-back; saved = read-back succeeded; failed/verification_failed = intervention needed. Use existing state for diagnosis, avoid spawning duplicate monitors. Semantic duplicate detection is best effort; exact event IDs and write retry paths are idempotent.

The foreground skill still performs task-specific retrieval and can save verified lessons. Check existing notes before adding another; do not duplicate the listener's captures. Native UserPromptSubmit hooks retrieve history for the current question and project; unchanged results are suppressed.

当前增强入口与证据边界见 [enhanced-memory.md](enhanced-memory.md)。
