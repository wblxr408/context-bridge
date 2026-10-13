## Design Principles

1. **Design for the agent, not the human** — Test output, docs, and task structure are the agent's primary interface
2. **Progress files ARE the context** — When context window resets, progress files + git history = full recovery
3. **Premature completion is the #1 failure mode** — Structured task lists with explicit completion criteria prevent declaring victory early
4. **Standardize everything grep-able** — ERROR on same line, structured timestamps, consistent prefixes
5. **Fast feedback loops** — Pre-compute stats, run smoke tests before full validation
6. **Idempotent everything** — Init scripts, task execution, environment setup must all be safe to re-run
7. **Fail safe, not fail silent** — Every failure must have an explicit recovery strategy
