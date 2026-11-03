# Otari integration feedback

Based on the recorded Windows application validation on November 3, 2026.
Request-level evidence is in [hosted acceptance](OTARI_HOSTED_ACCEPTANCE.md) and
[fallback and answer-quality acceptance](OTARI_FOLLOWUP_ACCEPTANCE.md).

## When was calling a provider directly most tempting?

The largest integration friction was obtaining observable code and MCP execution
results. The tested hosted Chat Completions requests returned billed prose without
the corresponding inspectable top-level execution records, although web-search
records were available. For example, request
`26bd1e88-e9c7-4cae-aeb2-4c421794d57a` did not establish that code had executed.
Switching the application to Messages native results, using the dated code tool
declaration and the MCP beta, supplied actual stdout, exit status and completed MCP
reads. Clear per-endpoint capability/version information would have saved time.

Strict schema decoding on one Nebius synthesis request also emitted repeated
whitespace until the output limit. The application now supports a per-role JSON
object carrier while retaining full local JSON Schema validation. The observed
failure remains in the acceptance evidence; this is not a claim about every model
or every strict-schema request.

## What did the application have to build itself?

Bridge added a persistent task journal, immutable source snapshots, exact quotation
checks, evidence-scope filtering and a bounded candidate/review/revision gate.
Those application responsibilities remain useful. Gateway integration would be
easier with consistent native tool-result envelopes, explicit cost-unknown fields,
and clearer replay guarantees for each transport.

A non-streaming repeated request returned an idempotent cached result. A repeated
Messages stream did not carry a replay flag and was charged again. The application
therefore blocks automatic redispatch of uncertain streams and requires
reconciliation. Highlighting this difference directly beside the idempotency
examples would help consumers avoid assuming every transport is safe to replay.

## Would the project continue using Otari without the hackathon requirement?

The tested routing, multi-provider visibility and hosted spend ceilings are useful
reasons to retain it. A real controlled DeepInfra 404 was absorbed and served by
Nebius on attempt two; a hosted budget refusal and same-task recovery were also
observed. An OpenAI-compatible boundary allowed this integration without replacing
the existing Markdown memory base or SQLite runtime.

Continued use should remain conditional on the transport and tool-record contracts
the application actually needs. The project does not assume that a configured
feature executed, that an exact quote guarantees correct reasoning, or that every
failure can fall back after streaming begins. Improvements to tool visibility and
transport-specific replay documentation would make that decision easier.

## Bounded validation

Cumulative reported spend was USD 0.115487, including failed exploration, semantic
reviews and revisions, with no unknown-cost calls. The USD 0.20 never-reset ceiling
remains. The temporary read-only MCP endpoint is closed. The new English video
reuses saved results and adds no paid model calls.
