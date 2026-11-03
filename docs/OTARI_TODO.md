# Developers Wilding — competition branch TODO

Branch: `codex/otari-devs-wilding`, based on public `main` at `02a549e`.
Goal: implement an evidence-backed memory workbench using the hosted Otari gateway,
with two open-weight model roles and six demonstrated gateway capabilities.
This is ordinary task documentation; no new OpenSpec change is being created.

## Completion contract

- [x] A. Hosted gateway adapter: explicit extraction/reflection models or routing policies;
  environment-only credentials; schema validation; bounded requests; typed refusals;
  request IDs, actual model/fallback, tokens and priced/unknown costs preserved.
- [x] B. Existing listener and reflection use the selected backend and existing shared budgets.
  Exact source support remains mandatory; invalid results never become accepted memory.
- [x] C. Resumable research workflow: retrieve memory, discover current official sources
  through Otari web tools, materialize source text, synthesize cited answers, and
  retain intermediate evidence and failures for continuation without repeated effects.
- [x] D. Otari code analysis consumes actual run records, returns its execution results,
  and distinguishes generated analysis from the gateway's authoritative accounting.
- [x] E. Read-only HTTP MCP exposes only scoped search, source reads and revisions.
  Otari can use it through a reachable HTTPS endpoint; model-generating tools and
  memory writes are excluded from this remote tool loop.
- [x] F. Local workbench: task/answer, inspectable sources, timeline/model/tool/cost
  evidence, loading/empty/error/budget states and resume; accessible responsive UI.
- [x] G. Focused behavior acceptance: latest correction, absent evidence, changed web
  sources, fallback, budget refusal, malformed output, interruption/resume and MCP bounds.
- [x] H. Delivery: reproducible setup, example configuration without secrets, demo data,
  rubric evidence map, participant-recorded 3–5 minute demo outline and written feedback.
- [ ] I. Hosted acceptance: real requests for both model roles, web/code/MCP, actual
  routing and budget behavior; record remaining unverified items honestly.
  Subsequently authorized with a USD 0.20 ceiling. Both models, web, code, remote
  MCP, named routing and hosted budget refusal/recovery have real evidence.
  Actual provider fallback remains unverified; see [hosted report](OTARI_HOSTED_ACCEPTANCE.md).

## Stages and evidence

1. Gateway and memory integration (A–B): focused RED/GREEN consumer tests.
2. Research, analysis and continuation (C–D): observable persisted business effects.
3. HTTP MCP and workbench (E–F): protocol behavior and browser user journeys.
4. Acceptance and delivery (G–I): real hosted capability evidence and submission material.

No mocks, fixtures, dashboard switches or old test reports count as hosted execution.
The theoretical rubric coverage is 30 + 60 + 10; it is not an awarded score.

## Decisions and boundaries

- Reuse Python, the existing Markdown vault, memory runtime and SQLite state; no new
  default memory service or background listener. The contest workbench runs explicitly.
- HTTP transport uses Python's existing standard library. JSON Schema validation uses
  `jsonschema` rather than a home-grown subset; the MCP transport will reuse the installed
  official MCP SDK where its current public contract fits.
- The web UI uses local static HTML/CSS/JavaScript served by the Python application,
  avoiding a second package/build/runtime for this bounded personal workbench.
- This retains the existing runtime, deployability and maintainability. Rust/Go or a
  separate React service would introduce migration and IPC/deployment work without an
  identified performance requirement. Resource/latency claims require measurements.
- Six target features: routing/fallback, budgets, distinct model roles, web retrieval,
  code execution and MCP. Guardrails are a candidate extension: the inspected hosted
  account had no guardrail service configured. Per-user budgets are out of this scope.
- No changes to the installed personal listener or native client configuration.
- Public deployment, new persistent credentials, purchases, videos and messages require
  their concrete workflow/authorization; implementation does not imply they occurred.

## Current state

2026-11-03: canonical public repository cloned into `D:/context-bridge-otari` and isolated
competition branch created. Implementation is local; the saved Cloud preference maps to
`wblxr408/ContextRail`, a distinct repository. Existing ContextRail changes are untouched.

Stage 1 was committed and pushed as `2177c03`. Stage 2 adds opt-in research tasks in
the existing SQLite database and immutable Markdown source snapshots in the vault's
`.otari-sources` directory (excluded from automatic memory recall). It does not install
a service. Prepared request inputs, gateway settings and operation keys survive retries;
known results are reused. An abandoned worker lease expires after 15 minutes.
Stage 2 was committed and pushed as `3c937e3`. Stage 3 implements the local
workbench and a separate authenticated MCP-only HTTP app, using the official MCP
SDK 2.2 transport. Both bind loopback by default. Remote publication additionally
requires an exact scope and explicit permalink allowlist; it cannot invoke models
or write memory. At that stage external HTTPS reachability had not yet been verified.
Stage 3 was committed and pushed as `7615ac1`. Stage 4 closes current-change recovery
and evidence gaps and delivers [setup](OTARI_GUIDE.md), [demo/submission material](OTARI_SUBMISSION.md)
and fictional [demo data](demo/conversations.json). The user then instructed us
to complete code/materials and defer credential configuration. Implementation is
local in `D:/context-bridge-otari`; installed listeners and `D:/ContextRail` are untouched.

The subsequent authorized hosted phase has now run, with request IDs, costs and
failures in the hosted report. Remaining work: actual provider fallback, a coherent
participant-run demonstration, eligibility/timezone confirmation and participant videos.
Submission mail has not been sent.

## Sources

- https://otari.ai/devs-wilding
- https://docs.google.com/document/d/1-spnCZ3f2SSki8cb6FnochjchdyttUsjjxfoE6aBnF4/edit
- https://github.com/mozilla-ai/otari/blob/main/docs/api-reference.md
- https://github.com/mozilla-ai/otari/blob/main/docs/tools.md
- https://github.com/mozilla-ai/otari/blob/main/docs/mcp.md
- https://github.com/mozilla-ai/otari/blob/main/docs/routing.md

## Verification log

Stage 1: gateway consumer tests first failed because the selected backend still
launched Codex (five failed assertions); implemented dispatch and transport, six
gateway cases passed. Memory integration next failed on absent call history and
unreported tokens (`None + None`); settlement and persisted gateway history added.
Both memory consumer cases passed. Eight new focused cases passed across the two
current-change test modules; unchanged existing suites were not run.
All endpoints in these tests are local contract fixtures, not hosted execution.

Stage 2: eight new workflow cases initially failed (seven assertions and one missing
source outcome). The implementation exposed a test-data keyword mismatch and strict
canonical-path handling of not-yet-created snapshot folders; both were corrected.
All eight current-change workflow cases pass: grounded official sources, interruption
and exact-input resume, one reservation per logical call, missing quote rejection,
budget pause/resume, immutable changed-source revisions, absent execution proof,
insufficient evidence and domain rejection. The gateway and source loader are injected
fixtures here; these results do not establish hosted tool availability or billing.

Stage 3: six new HTTP outcomes initially failed (five assertions and one absent task
identity). All six pass after implementation, including actual MCP initialize/list/
read/search/revision protocol calls and rejected unpublished sources/authentication.
Browser acceptance exercised submit → answer → exact source quote, execution details,
refresh → persisted task reopen, keyboard tab switching and 1440/390 layouts. The
mobile document did not overflow its viewport; no captured browser warning/error.
The browser backend used the stage-2 scripted tool fixture, not hosted Otari.
Desktop screenshot: `%TEMP%/bridge-workbench-desktop.jpg`; mobile screenshot:
`%TEMP%/bridge-workbench-mobile.jpg`. Fraunces font is bundled under its OFL license.
On this Windows host fixed ports 8765 and 49723 returned bind error 10013; an
OS-assigned port worked for the browser journey. Use a permitted port when launching.

Stage 4: four delivery contracts found two real gaps (remote reads were logged but
not used in answers, and abandoned leases had no UI resume signal). Both fixed;
all four pass, also covering latest explicit correction and one retained memory event
after interruption during derived-page publication. Four additional boundary cases
failed on malformed-output charge metadata, expired replay, missing operation-level
reservation binding and string tool flags. All four pass after fixes. Prepared
requests over 23 hours old stop for reconciliation; transactionally bound operation
IDs prevent a second reservation across a task-journal gap. Current-change coverage
totals 30 passing cases across the staged runs, not a fresh run of unchanged suites.
No legacy regression, startup/import probes, checksum comparisons or smoke checks run.

At the end of Stage 4, the hosted phase was deferred by explicit user choice.
Demo/submission descriptions remained drafts. Later evidence below supersedes this
historical hosted status; no competition submission was sent.

2026-11-03 follow-up: user supplied the Maple Ridge House design reference and
authorized local encrypted credential storage. The workbench now uses its cream/
taupe soft-UI, Poppins/Roboto Mono, task grid, segmented history filters and actual
task/accounting indicators; see [design and acceptance](OTARI_DESIGN.md). Four new
dashboard contracts pass; old suites were not rerun. User credential is stored outside
the repository with Windows user DPAPI, injected only into the launched process by
an ignored local launcher. Authenticated model-catalog retrieval returned 159 entries.
This resolves credential setup, not hosted inference/tool/routing/budget acceptance.

2026-11-03 hosted continuation: user authorized USD 0.20 total and the temporary
HTTPS publication of one existing fictional note with three read-only tools.
Real extraction/retention/citation, web search/materialization/exact quotes, sandbox
code/stdout/exit 0, remote MCP search/read and adopted versioned quotation, and an
Otari spend-ceiling refusal followed by same-task recovery were recorded. A named
route served a request. Attempted unavailable-primary fault injection was rejected
by Otari's configuration validation; no actual fallback record was obtained.
The normal route remains valid; no provider credentials were changed.

Hosted findings drove bounded fixes: role-level reasoning, output-limit rejection,
workbench-specific preference extraction and grounded synthesis, readable HTML
paragraph extraction preserving pre blocks, and Messages native code/MCP results.
Uncertain streams require reconciliation rather than re-dispatch: a real repeated
stream was charged despite the same operation key. The extra USD 0.011151 is included
in the reported USD 0.085749 total, rather than hidden outside the app's ledger.
Current-change RED/GREEN: 4 reasoning cases, 3 HTML evidence cases, 6 native tool and
recovery cases. No unchanged regression suite was run.

Tunnel and demo MCP process stopped; Otari server disabled, temporary token removed,
active local MCP IDs cleared. The USD 0.20 never-reset ceiling remains, without
clearing spend. Model, cost, source and semantic-quality limits are documented in
[OTARI_HOSTED_ACCEPTANCE.md](OTARI_HOSTED_ACCEPTANCE.md).
