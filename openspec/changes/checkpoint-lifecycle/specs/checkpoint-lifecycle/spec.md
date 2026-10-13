## Purpose

Safely retire personal checkpoint originals while retaining protected recovery points and factual, on-demand task history. Lifecycle state distinguishes quarantine, restoration and irreversible deletion without treating summaries as current instructions.

## ADDED Requirements

### Requirement: Protected and bounded selection
The system SHALL group exact agent/session identities, preserve unknown, pinned, in-use and latest unfinished recovery points and explicit original dependencies, and treat a requested percentage as a soft target.
#### Scenario: Protected points prevent eighty percent
- **WHEN** keeping protected points leaves fewer candidates than the requested percentage
- **THEN** only reviewed candidates are selected and the shortfall is reported

### Requirement: Factual historical summaries
The system SHALL publish one active historical summary per task with reviewed source identities, count it with a fixed recorded tokenizer, reject more than 2000 tokens, and retain originals if summary publication or read-back fails.
#### Scenario: Summary exceeds its budget
- **WHEN** a supplied historical summary exceeds 2000 measured tokens
- **THEN** no source is quarantined and rewriting is required
#### Scenario: Reviewed history revision during an earlier quarantine
- **WHEN** a reviewed revision incorporates the existing task history while older originals are quarantined
- **THEN** the previous summary remains available through the latest associated deadline, earlier original expiry remains unchanged, and interrupted publication recovers before deleting an original

### Requirement: History is on demand
The system SHALL exclude history summaries and their derived content from automatic hooks, current reflection, current pages and automatic native context. Explicit historical queries SHALL remain available.
#### Scenario: Same history question enters a prompt hook
- **WHEN** a history summary matches a UserPromptSubmit query
- **THEN** the summary is excluded from automatic additionalContext

### Requirement: Two lanes preserve real quarantine time
The system SHALL use ordinary 24-hour source and 72-hour quarantine intervals and a configurable fast interval defaulting to 60 minutes. Replayed events SHALL NOT reset or silently shorten existing quarantine deadlines.
#### Scenario: Fast boundary
- **WHEN** a source has been quarantined for 59 minutes
- **THEN** it remains recoverable; at 60 minutes it is eligible for permanent deletion after protection is rechecked

### Requirement: Restore and expired cursor semantics
The system SHALL restore an isolated original without overwriting another file and pin the restored point. A deleted exact cursor SHALL report deletion and its history summary without claiming exact restoration.
#### Scenario: Destination was recreated
- **WHEN** restoration finds a conflicting live source at its original path
- **THEN** it rejects the operation and retains both existing data and quarantine

### Requirement: Restartable cleanup and cache invalidation
The system SHALL reject stale identities, revisions, source versions and unsafe paths, log operation identities before mutation, recover interrupted transitions, unload original-derived indexes and use only the existing listener for due maintenance.
#### Scenario: Protection changes after planning
- **WHEN** a checkpoint becomes pinned after a plan was generated
- **THEN** applying the stale plan rejects it and leaves its original intact
