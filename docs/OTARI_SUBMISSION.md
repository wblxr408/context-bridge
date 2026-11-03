# Bridge — Otari hackathon submission

Registration and prize eligibility were confirmed by the organizer on November 3,
2026. The confirmed deadline is **November 11, 2026, 23:59 EST**
(**November 12, 2026, 12:59 Asia/Shanghai**). The English demonstration and written
feedback below are prepared for submission in the original signup email thread.
Email delivery and acceptance of the supplied video are separate states.

Official sources: [event and submission requirements](https://otari.ai/devs-wilding)
and [judging rubric](https://docs.google.com/document/d/1-spnCZ3f2SSki8cb6FnochjchdyttUsjjxfoE6aBnF4/edit).

## Project

**Bridge: evidence-backed memory that can resume.** Context Bridge gives Codex and
Claude Code source-backed long-term memory and resumable research tasks, with
Otari-hosted inference, inspectable tool results and request-level accounting.

The competition branch reuses the existing Markdown memory base and SQLite
runtime. Separate model roles handle extraction, synthesis and tools. The
workbench keeps immutable source snapshots, quotations, prepared requests,
request identifiers, served models, fallback reports and reported or unknown costs.
An authenticated HTTP MCP service exposes only selected read-only demo sources;
the temporary hosted-acceptance endpoint is now closed.

- Repository: [wblxr408/context-bridge](https://github.com/wblxr408/context-bridge).
- Hackathon branch: [`codex/otari-devs-wilding`](https://github.com/wblxr408/context-bridge/tree/codex/otari-devs-wilding).
- First Otari integration: [commit `2177c03`](https://github.com/wblxr408/context-bridge/commit/2177c03).
- Otari repository PRs/issues opened for this work: none.
- The Otari signup email is supplied privately in the submission email.

## Features with hosted application evidence

- Open-weight extraction and synthesis roles, including DeepInfra Qwen3.5-35B-A3B,
  Nebius Qwen3-30B-A3B-Instruct-2507 and Qwen3.5-397B-A17B for bounded quality work.
- Routing and fallback: a controlled incompatible-model request produced a real
  DeepInfra `404 model_not_found`; Otari absorbed it and Nebius served attempt two.
  This is a controlled failure experiment, not a provider outage claim.
- Hosted spend ceilings: a real refusal followed by recovery of the saved task
  with its original operation key.
- Web search: an official Python documentation result retained as a source snapshot.
- Sandbox execution: native Messages records retained stdout and exit status.
- Remote MCP: completed read-only source lookup/read records retained before the
  temporary endpoint was closed. Saved-source reuse avoids republishing personal memory.

See [hosted acceptance](OTARI_HOSTED_ACCEPTANCE.md),
[fallback and answer-quality acceptance](OTARI_FOLLOWUP_ACCEPTANCE.md),
[hosted request evidence](otari-hosted-evidence.json) and
[follow-up request evidence](otari-followup-evidence.json).

Exact quotations alone did not ensure relevant reasoning. Failed reviewer results
are retained. Source filtering and a bounded candidate/review/revision gate improved
the tested answers, with abstention when evidence remained insufficient; these
finite checks do not establish general accuracy. Unknown stream outcomes require
reconciliation rather than an automatic replay that might be billed again.

## Demonstration and feedback

- [Four-minute English demonstration](demo/bridge-demo-en.mp4).
- [English subtitles](demo/bridge-demo-en.srt) and [narration script](demo/bridge-demo-en-script.md).
- [Production details](OTARI_VIDEO.md).
- [Written feedback answering the official questions](OTARI_FEEDBACK.md).

The video uses AI-assisted editing and synthetic English narration. Its recorded
English evidence view translates saved Chinese sources and does not claim a new
live inference or participant-spoken recording. The published rubric prohibits AI
demo/video feedback and requires participant audio. The submission discloses this
production method and asks the organizer to assess whether this video can be
accepted; registration confirmation does not waive that separate requirement.

The English edit added no paid inference. Recorded validation spend remains
**USD 0.115487**, within the user's cumulative USD 0.20 ceiling. The event-credit
voucher does not raise that authorized spending limit.
