# resume-tailor Dev Log

## Working State
**Session:** 3 | **Date:** 2026-04-30

### Active Task
GitHub readiness — 6 pre-push fixes

- [x] Fix 1: README.md written
- [x] Fix 2: master.md gitignored + master.example.md created
- [x] Fix 3: client.py CLI shim removed — API-key-only path
- [x] Fix 4: model name `claude-sonnet-4-5` documented (verify on console before running)
- [x] Fix 5: DEVLOG Working State updated
- [x] Fix 6: B3/B4 documented as known TODOs in README

### Key Files (current shape)
**`src/resume_tailor/client.py`** (MODIFIED, ~15 lines)
Stripped to API-key-only singleton. Raises RuntimeError if ANTHROPIC_API_KEY is missing.

**`master.example.md`** (NEW)
Public placeholder bullet library. Explains format, voice labels, and slug conventions.

**`README.md`** (NEW)
Public-facing setup guide, pipeline diagram, scoring table, known limitations.

**`src/resume_tailor/subskills/ranker.py`** (~210 lines)
Scores every bullet against 5 weighted factors. anchor_match reads anchor_metadata.hard_requirements; gap_relevance does slug match first, text fallback.

**`src/resume_tailor/main.py`** (~217 lines)
Orchestrator. Auto-deletes 2A/2B scratch when step 1 re-runs (new JD). Prints gap report + operational context at end.

### Decisions (active)
- master.md gitignored — personal data never leaves local machine
- CLI shim removed — was never reliable (timeouts, org restrictions); API key is the only path
- B3/B4 documented as known TODOs rather than patched (scope too large for pre-push)

### Next Steps
1. `git add -A && git commit && git push` — repo is ready
2. Get API credits and run first full end-to-end test
3. Verify model name on Anthropic console

### Watch Out
- master.md is gitignored — contributors must cp master.example.md → master.md
- Bullet IDs are hash-based (sha1 6 chars) — stable across reorders. But if you change bullet text the ID changes and scratch/02a becomes stale.
- 200-char limit excludes `**bold**` markers — validator strips them before counting

---
---

## Session Archive

### Session 2 — 2026-04-27 → 2026-04-29: Schema upgrade + cache hardening
**What we did:** Upgraded JD analyzer schema (anchor_metadata, gap_mapping, narrative_strategy, operational_context). Ranker updated to slug-match gap_mapping. Auto-delete stale 2A/2B scratch when step 1 re-runs on a new JD. Payload slimming (~35%) for 2B. Compressed resume_selector system prompt (~1850 chars). Investigated CLI/OAuth paths — both dead ends; API key is the only reliable path.
**Files:** prompts/jd_analyzer.py, prompts/resume_selector.py, subskills/jd_analyzer.py, subskills/ranker.py, subskills/resume_selector.py, main.py, client.py
**Decisions:** CLI shim abandoned (timeouts + org restrictions). master.md stays gitignored; example file added for public repo.

### Session 1 — 2026-04-27: Full pipeline build
**What we did:** Built complete 5-step pipeline from scratch — JD analyzer, ranker, resume selector, LaTeX editor, tracker. Refactored Step 2 into 2A (Python) + 2B (Claude). Fixed 8 bugs (empty allocation, ID hallucination, retry, voice-label warning, summary anchor, skills dead code, techstack removal, state persistence).
**Files:** All files under src/resume_tailor/
**Decisions:** Proportional topic allocation, master.md parsed at runtime, techstack frozen.
