# Design

## Context

Reuse v4 source planning in ../.. external checkpoint-lifecycle-plan. Main has191 typed checkpoints/51 exact session groups at the last inventory. Existing schema2 retention remains the local bundle owner; this implementation adds a BM lifecycle branch. The user cancelled queue trimming and now authorized deployment and protected best-effort80% cleanup.

## Goals / Non-Goals

**Goals:** reviewed batch maintenance, exact tombstones, on-demand task history, source/cache retirement, ordinary and fast lanes and due cleanup in the same listener.

**Non-Goals:** automatic inference that an open task is completed, deleting unique recovery requirements to hit80%, queue deletion, knowledge-base daily/weekly merger, new daemon or long-term raw archive.

## Decisions

Authority is atomically versioned checkpoint-lifecycle.json plus an operation record outside main; SQLite holds only rebuildable retrieval caches. Originals move into a dedicated service quarantine outside vault scans; real source/destination canonical containment and reparse-point rejection precede each mutation. A cooperative maintenance gate serializes lifecycle changes. Interrupted moving/purging/restoring states are recovered from the journal and exact source identity, never silently overwritten.

Group by agent/session_id and normalized cwd; shared identity alone does not merge a chat that switched projects. Keep latest unfinished per group, explicit pinned/in_use/depends_on and operator-protected active sessions. Lineage links are historical navigation, not automatically an original requirement. Exact semantic review records identify candidate source versions and protected unique requirements. A percent plan chooses oldest reviewed candidates, and reports protected shortfall. Defaults: same task>8 target3, project/folder>20 target10, ordinary24/72hours, explicit fast batch60minutes. No proof of ownership means preservation.

A supplied reviewed draft or factual extraction produces a per-task checkpoint_history note in main. The recorded multilingualMiniLM tokenizer measures whole rendered summary; less than1000tokens is permitted for genuinely short history, more than2000rejects. Source facts are checked against originals before publication; preservation of key numbers, negative results and revisions is an operator semantic review, not a model score. Existing summary revisions increment, previous summary version retained only until the last associated quarantine deadline. Semantic model generation is optional and consumes existing shared budget; this deployment uses reviewed foreground drafts and no extra model calls.

Default/current retrieval, prompt hooks and generated pages exclude checkpoint_history and metadata auto_inject=false; explicit history query may include them. Native automatic context response filtering and exact retired-cursor handling extend the same proxy. Deleted checkpoints return an explicit tombstone and summary path; quarantined exact reads return the original with isolation status. Existing unsupported other-project MCP contracts continue native delegation.

Quarantine invalidates vector/passages/page/injection caches and source-derived owned pages, native Basic Memory synchronization removes deleted originals from its accepted search index. Every live query reconciles removed paths. Source deletion does not remove shared facts backed by independent evidence. Listener's existing maintenance cadence handles purge_after; no polling daemon, new catalog or automatic thread.

## Risks / Trade-offs

Summary is lossy; keep unresolved unique requirements or the current exact recovery original. Existing checkpoints mostly status=open, so do not infer task completion from age or notLoaded. Existing clients may cache old proxy code; deploy filters and native index synchronization before isolation, and protect currently active sessions. Cooperative locks cannot stop protocol-external readers; protect uncertain actual readers.

## Migration Plan

One-time operator exception on 2026-10-12: the user explicitly authorized chronological deletion of the oldest80% for this batch. A separate frozen194-note ledger selected155 by valid UTC checkpoint time and kept39. Before any deletion,42 reviewed histories were written/read back through native Basic Memory;155 exact native deletions then succeeded and both native search and vault inventory confirmed all39 retained points. This exception does not change the default protection/real-quarantine rules above. Global lifecycle installation remains pending because this execution environment has not granted write access to the service/skills; the batch did not claim that tombstone interception or scheduled expiry was deployed.

Observe consumer RED for automatic history leakage and unsupported lifecycle CLI, implement functional and recovery tests, run affected regression. Acquire existing writer lock, preserve a consistent state backup and old code/config, install new code/rules, freeze live protection, prepare/readback summaries, apply reviewed plan, native sync, resume original task. Due originals are deleted only after actual quarantine period; immediately report isolation and future eligibility separately. No long-term raw corpus ZIP is created. Before purge, restoring exact candidates can undo the batch; after purge only summary remains.
