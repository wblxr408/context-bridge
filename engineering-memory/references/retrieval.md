## Proactive retrieval

- Retrieve before answering questions about previous decisions, work, or user conventions, and before resuming work that depends on that history. Explicit user requests to retrieve always trigger retrieval.
- At the start of project implementation, diagnosis, planning, research, review, or technical questions that plausibly depend on personal engineering knowledge, retrieve relevant decisions, constraints, and pitfalls before planning or answering. Generic explanations, trivial chat, copy edits, and tasks with no plausible dependency on personal history can skip retrieval.
- Before consequential decisions about architecture, technology, frameworks, libraries, packaging, deployment, databases, concurrency, performance, security, builds, or CI/CD, ensure the relevant history has been retrieved and read.
- Reuse already-read notes within the same task while their scope and evidence remain applicable. Do not repeat searches for ordinary follow-up messages. Search again when the project, technology, environment, constraints, or error changes, new evidence contradicts the notes, or the plan is about to change materially. After handoff or context loss, retrieve needed notes if their substance and applicability are no longer available.
- Start with `search_notes(project="main", search_type="text")` and relevant technology names and keywords, then read relevant notes. If results are empty or irrelevant, make one focused reformulation, using broader terms or a full-title search for Chinese text. If that also finds nothing relevant, proceed with current evidence; revisit only when new information supplies a reason. An empty result is not a connection failure.
- Prefer `status: verified`, then `experimental`, but check context, applicability, exclusions, technologies, platforms, verification date, and evidence. Current verified evidence overrides stale notes. Explain material conflicts and correct or supersede the old entry with evidence and a reason.

Session-start context is orientation; it does not substitute for task-specific retrieval. Normally keep retrieval quiet. Explain when memory changes the chosen approach, avoids a known problem, conflicts with current evidence, or cannot be accessed. Do not announce every routine search.

当前增强入口与证据边界见 [enhanced-memory.md](enhanced-memory.md)。
