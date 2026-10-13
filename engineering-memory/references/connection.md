## Connection fallback

If native tools are absent or fail to connect, automatically use the read-only fallback through the same configured Basic Memory MCP:
`& 'C:\Users\wblxr\anaconda3\python.exe' 'C:\Users\wblxr\.codex\bin\basic-memory-query.py' --query 'relevant keywords' --project main`
Use `--identifier 'permalink'` to read a note, `--search-type title` for full-title search, or `--health` for diagnosis. The helper has bounded timeouts and retries a transient transport failure once. If it also fails, report the limitation briefly and stop repeated connection attempts for this task until recovery evidence, a meaningful environment change, or an explicit retry request occurs. Continue independent work using current evidence; do not invent historical facts or claim retrieval succeeded. When a decision depends on unavailable history, state that uncertainty. Connection diagnosis requested by the user may make targeted recovery attempts.

当前增强入口与证据边界见 [enhanced-memory.md](enhanced-memory.md)。
