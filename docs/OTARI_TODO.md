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
- [ ] C. Resumable research workflow: retrieve memory, discover current official sources
  through Otari web tools, materialize source text, synthesize cited answers, and
  retain intermediate evidence and failures for continuation without repeated effects.
- [ ] D. Otari code analysis consumes actual run records, returns its execution results,
  and distinguishes generated analysis from the gateway's authoritative accounting.
- [ ] E. Read-only HTTP MCP exposes only scoped search, source reads and revisions.
  Otari can use it through a reachable HTTPS endpoint; model-generating tools and
  memory writes are excluded from this remote tool loop.
- [ ] F. Local workbench: task/answer, inspectable sources, timeline/model/tool/cost
  evidence, loading/empty/error/budget states and resume; accessible responsive UI.
- [ ] G. Focused behavior acceptance: latest correction, absent evidence, changed web
  sources, fallback, budget refusal, malformed output, interruption/resume and MCP bounds.
- [ ] H. Delivery: reproducible setup, example configuration without secrets, demo data,
  rubric evidence map, participant-recorded 3–5 minute demo outline and written feedback.
- [ ] I. Hosted acceptance: real requests for both model roles, web/code/MCP, actual
  routing and budget behavior; record remaining unverified items honestly.

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
