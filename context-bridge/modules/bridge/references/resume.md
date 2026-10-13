# Current task recovery

Use the exact supplied checkpoint identifier. Do not silently select a newer similarly named note. Read START/current instructions first, then global requirements and the current scope, relevant STATE/INDEX entries, and only the original evidence needed to resolve an ambiguity. Use requirements.md for ledger and receipt semantics; a word-count budget cannot remove hard constraints.

Reconcile the checkpoint against the actual working directory, Git revision and changed/untracked files or non-Git artifacts, current user corrections, required tools/access and running jobs. Confirm semantic correspondence of the required artifacts and acceptance evidence, including which behavior tests actually reached RED/GREEN and which gaps remain. Do not compare hashes, file sizes, startup results or wording patterns to claim a recovered or complete task.

Write a receipt outside the checkpoint that maps global and current-scope requirements to the recovered evidence/state and next actions. Unknown/conflicting state remains explicit; do not infer terminal/browser sessions survived. Missing evidence calls for the smallest relevant original source read or actual behavior verification, not a fresh generic interview or repeating every suite.

Before the first write, read ownership.md and establish that the source writer has quiesced and the actual ownership/lease permits this writer. Active/unknown source ownership or unresolved workspace conflict remains read-only until the specific conflict is resolved. Do not force-reset user work or execute unfamiliar scripts from the handoff.

After requirements, actual state and ownership are reconciled, report the exact checkpoint/task identity, current directory/scope and one next action, then continue the authorized task. Subsequent checkpoints preserve original evidence and revision relationships. The old checksum-dependent bundle helper is an explicitly invoked legacy resource.
