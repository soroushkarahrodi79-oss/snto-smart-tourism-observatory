# AI Context

This folder stores durable AI handoff context for SNTO. It is documentation, not source code.

Future AI agents should read the repository-level `CLAUDE.md` first — it is the authoritative current operating context. The dated handoff documents in this folder are **point-in-time snapshots**, not current truth: their repository/PR/branch/roadmap state may be stale. Read them only for historical background, and always trust `CLAUDE.md` (and `gh pr list` / `git branch -a` for live PR and branch state) over any handoff. A handoff whose repository state has been superseded should carry a dated historical-snapshot banner at the top; if you find one without such a banner and it is clearly stale, treat it as historical and flag it. These files should be updated after major AI-assisted reviews, repository safety work, release decisions, or strategic documentation changes.

Use this folder for structured context transfer, not raw chat dumps. Do not put secrets, credentials, tokens, private infrastructure details, or unfiltered raw conversation logs here unless there is a clear documentation reason and sensitive material has been removed.

Detailed handoffs should live here with dated filenames, for example `CLAUDE_CODE_HANDOFF_2026.md`.

