## ADDED Requirements

### Requirement: Native integration preserves existing ownership
The system SHALL extend the existing Basic Memory main MCP bridge and listener, preserve unsupported request contracts and share the existing model budget.
#### Scenario: Existing model calls consume the quota
- **WHEN** the hourly budget is exhausted by listener classifications
- **THEN** reflection is rejected before a model invocation and evidence-only retrieval remains available

### Requirement: Scoped hooks and recoverable historical ingestion
The system SHALL use the current question and workspace for native history injection and SHALL process explicitly selected history through the existing idempotent queue.
#### Scenario: Same chat changes project
- **WHEN** a later prompt selects another workspace
- **THEN** the hook returns that workspace's applicable history and excludes the previous project's private facts
#### Scenario: Explicit replay of old history
- **WHEN** a historical log is explicitly imported twice after initial baselining
- **THEN** it creates one queued business event without resetting the live cursor

### Requirement: Protected two-phase checkpoint retention
The system SHALL retain current, received, pinned, active, dependent and uncertain checkpoints and SHALL use explicit task/snapshot and plan identities for isolated recovery and cleanup.
#### Scenario: Registration changes after planning
- **WHEN** a checkpoint becomes in-use after a plan is generated
- **THEN** the old plan is rejected and no checkpoint is moved or deleted

### Requirement: Grounded multilingual retrieval
The system SHALL return relevant Chinese or mixed-language notes, support literal Boolean queries, deduplicate source identifiers, preserve citation and scope, and reject empty or invalid input. Current answers SHALL omit superseded policies unless history is explicitly requested.
#### Scenario: Chinese rephrasing
- WHEN a Chinese question rephrases a stored transaction retry policy
- THEN the policy is retrieved with its source and no unrelated repository facts leak.

### Requirement: Evidence-grounded evolving knowledge
The system SHALL retain exact source quotations, bind events to payloads, record contradiction history and refresh knowledge pages after added or deleted evidence.
#### Scenario: Delayed old decision
- WHEN an older decision arrives after a newer correction
- THEN the newer correction remains current and both source records remain inspectable.

### Requirement: Semantic version handoff
The system SHALL bind receiver coverage and writer ownership to explicit task/version identity without using checksum manifests for acceptance.
#### Scenario: Ownership transfer
- WHEN source ownership transfers to a receiver for a snapshot
- THEN the receiver can write only for that snapshot and the source claim is invalidated.

### Requirement: Deployment acquires existing writer ownership
The system SHALL acquire and hold the existing listener lock before replacing installed files or database state and throughout deployment or restore; disabling scheduling alone SHALL NOT establish writer exit.
#### Scenario: Disabled scheduler with an active writer
- **WHEN** the scheduler reports Disabled while the previous writer still holds the lock
- **THEN** installation waits for ownership and preserves that lock until mutation is finished

### Requirement: SQLite restore handles active WAL
The system SHALL restore SQLite state with SQLite's backup API.
#### Scenario: A live connection holds a newer budget
- **WHEN** a backed-up budget of 2 is restored after an active WAL connection changes it to 7
- **THEN** the live connection reads the restored budget of 2

### Requirement: Failed jobs are explicitly recoverable
The system SHALL require explicit event selection and a reason, preserve previous errors and all quota records, and reject unknown selections atomically.
#### Scenario: Explicit recovery is repeated
- **WHEN** a failed job is selected twice for recovery
- **THEN** it is queued once and its failure audit and model quota remain intact

### Requirement: Historical reports distinguish business outcomes
The system SHALL distinguish added events from queued and filtered events.
#### Scenario: An import contains a preference and courtesy
- **WHEN** the import adds one queued preference and one filtered courtesy
- **THEN** it reports two added events, one queued and one filtered; replay adds none
