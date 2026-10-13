# Current task handoff

Preserve the original objective, latest user corrections, scope and authorization, observable completion criteria, decisions with reasons, actual TDD/regression evidence, unresolved work and one next action. Use a new task/UTC identity in a persistent task-accessible directory; never overwrite an immutable checkpoint. A Basic Memory checkpoint can hold the narrative with pointers to actual project artifacts.

For a local handoff, use START.md for entry and next scope, STATE.md for verified/inferred/unknown facts, INDEX.md for artifact paths/versions/loading conditions and requirements.json for the versioned user requirement ledger. Preserve key raw evidence, user changes and uncommitted work needed for recovery. Follow requirements.md for the actual ledger semantics. A summary is not a full transcript backup.

Record the real project directory and Git/non-Git state, branch/revision, modified/untracked work, running jobs and how to reconnect, credentials-access limitations, completed functional evidence and remaining gaps. Git revision identifies committed source; it cannot prove the current workspace or behavior. Review that the ledger and artifacts support the next action and reflect current corrections; do not create a hash manifest or run bundle seal/verify as a handoff test.

When another writer may operate on the same files, read ownership.md at that boundary. Complete in-flight writes and use the existing supported ownership/lease mechanism; source_writer=active cannot imply transferred ownership. Locks and ownership tokens remain outside immutable/public bundles. Do not commit, stash, reset, delete or create a new chat simply to checkpoint.

Provide the exact returned memory identifier or absolute local checkpoint path, task/version identity, working directory, next scope and primary next action. Continue already-authorized work. Inspect retention.md only for an explicitly needed retention decision; use its current task/version registration protocol. Preserve uncertain versions and other tasks' files rather than invoking generic cleanup.
