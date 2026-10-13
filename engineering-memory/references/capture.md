## Event-driven capture

Actively assess new or changed knowledge when any of these events occurs:
- A fix or experiment produces a meaningful verification result: consider conditions, cause, remedy, and verification.
- An attempted approach fails and the failure conditions become clear, especially when a working alternative is found: consider what to avoid and why.
- A consequential decision is accepted, revised, or abandoned: consider constraints, rationale, alternatives, and conditions for reassessment.
- The user corrects the assistant or explicitly states a lasting preference: consider the precise convention and its scope; do not generalize a one-off request without evidence.
- A milestone is accepted, work is handed off, or a task finishes: consider reusable lessons and separately retain necessary unfinished work as task/checkpoint state.
- New evidence invalidates an existing note: consider correction or supersession, preserving why it changed.

These are semantic checkpoints inside the task. The user subsequently authorized a background listener for Codex and Claude Code, with periodic incremental reconciliation and failure recovery. Periodic checks alone do not justify a model call; only new candidate events enter the bounded semantic queue. Do not re-evaluate unchanged conversations on a timer or every N messages. Assess only the event's new or changed information using context already available. At task completion, check once for formed conclusions that have not yet been captured; do not rescan or resave unchanged material. Session start alone does not justify creating a knowledge note.

## Value, granularity, and evidence

Save a durable lesson when it contains new user/project-specific or hard-won information, could change a future action or avoid repeated work/loss, and is actionable with explicit applicability and evidence. Rare but costly failures can qualify without repetition. Clear recurring preferences can qualify on the user's explicit statement alone.

Use one note per independently retrievable, applicable, and maintainable lesson or decision. Keep one cause, its remedy, and verification together. Split conclusions with different applicability or independent update lifecycles. Update an existing matching note with new evidence; link related notes or an index instead of duplicating content. Do not create a note per message, command, or failed attempt.

Each durable note should explain context and applicability, the problem or decision, the action or conclusion, evidence, limitations or exclusions, and when to reconsider it. Include verification dates and relevant environment/version details when they matter. Add concise observations and meaningful relations to existing notes.

Match claims to evidence: mark technical conclusions verified only for what was actually tested or directly evidenced. Record useful unverified hypotheses as experimental with an explicit verification gap, or retain them in task state if they lack durable value. Record a chosen decision as accepted without implying its outcome has been validated. A user-stated preference is evidence of that preference, not proof of technical efficacy. Do not mark this workflow's long-term effectiveness verified merely because its configuration was saved.

Exclude ordinary action logs, generic advice, duplicate common knowledge, unexplained errors, transient progress, credentials, and secrets from durable lessons. Keep necessary short-lived progress and open questions in task or handoff records.

## Save and verify

For a qualifying event, extract the conclusion, search for matching notes (or reuse an already established match), read candidates, then update or create the smallest useful note and verify the saved content. The user authorizes proactive local capture under these rules; do not ask for routine confirmation. Preserve unrelated content and explain corrections to prior conclusions. Do not send or share notes externally without authorization.

Prefer Basic Memory write/edit tools. If those tools are unavailable, the confirmed local Markdown vault may be edited with normal file tools and then read through Basic Memory to confirm visibility; the read-only query helper cannot perform writes. If deduplication or verification is unavailable, preserve a task-local draft or explicitly pending capture and report its status, rather than claiming an indexed save. Avoid silently creating duplicates during an outage.

When nothing qualifies, continue quietly. After successful capture, briefly state what was saved, combining multiple captures into a milestone or final update when practical. Never report a save or verification that did not occur.

当前增强入口与证据边界见 [enhanced-memory.md](enhanced-memory.md)。
