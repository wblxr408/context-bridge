## Choose One Recall Route

Choose exactly one route from the invocation.

### Exact checkpoint

When the user supplies an exact Basic Memory identifier or permalink, read that note directly.
When `primaryProject` is configured, call `read_note` with both the exact
identifier and `project=<configured primaryProject>`. The explicit project is
required even when the identifier is a permalink, file path, or title. If setup
is missing, use the default project and say that the project scope could not be
verified. Do not retry the identifier against secondary or other projects, search
for alternatives, or silently substitute a newer checkpoint. The exact pointer
and project are the user's chosen cursor.

### Topic discovery

When the user supplies a topic rather than an exact identifier, search the
primary project for matching `task`, `decision`, and `codex_session` notes.

Run the `coding_session` topic search separately and include it only when
`sessionProfile=coding` and the configured `repository` is present. Apply
`metadata_filters={"repository": "<configured repository>"}` using the exact
configured value. Never let topic text similarity compensate for a missing or
mismatched repository. If the coding profile has no configured repository,
omit `coding_session` results and report that setup is incomplete.

- no credible match: report that no checkpoint was found and do not invent one
- one clear match: read it automatically
- multiple plausible matches: show at most three with title, type, timestamp,
  repository or branch when available, and permalink; then wait for the user
  to choose

Do not ingest an arbitrary filesystem path, folder, HTTP URL, or pasted handoff
as the memory source. A repository path may be used only as a search signal
against Basic Memory and current repository evidence.

### Current repository

When the invocation has no argument, query the primary project:

- active tasks: `type=task`, `status=active`
- open decisions: `type=decision`, `status=open`
- recent Codex sessions: `type=codex_session`, after `recallTimeframe`
- recent coding sessions: `type=coding_session`,
  `repository=<configured repository>`, after `recallTimeframe`, when
  `sessionProfile=coding`

Always query `codex_session`; include `coding_session` for a coding profile only
with the configured `repository` metadata filter. Never run an unscoped
coding-session query; if the repository is missing, report that setup is
incomplete. Merge and deduplicate the results, sort them newest first, and
prefer the highest-signal checkpoint regardless of which producer wrote it.
`coding_session` carries schema-required, queryable Git context;
`codex_session` preserves general and legacy Codex checkpoints. Do not query
lifecycle trace: `bm hook flush` archives it locally and never promotes it into
the graph.

Query configured `secondaryProjects` read-only for open decisions. Do not write
to shared projects during orientation.

Read the highest-signal hits before summarizing. Prefer notes that match the
current repository, branch, Git SHA, pull request, named route, issue, or file
path. For coding sessions, use structured metadata filters before text search.
