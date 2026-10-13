## Confirm

Reply with:

1. one sentence summarizing what the checkpoint preserves
2. the exact resume identifier selected from the successful JSON result
3. the one primary next action
4. exactly one fenced resume command as the final block:

```text
$bm-orient "<exact returned resume identifier>"
```

Choose the first non-empty returned value in this order: `permalink`,
`file_path`, then `title`. Use the returned value verbatim; never construct or
guess a permalink or file path.
