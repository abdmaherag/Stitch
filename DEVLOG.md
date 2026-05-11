# resume-test Dev Log

## Working State
**Session:** 2 | **Date:** 2026-05-11

### Active Task
Pipeline fully wired and template-aligned. master.md populated with real career content. Edge case for underfilled slots added. Ready for first end-to-end real-JD run.

- [x] Install deps (docxtpl, docx2pdf, pywin32 — all import OK)
- [x] Run setup.py — scaffolds generated
- [x] Surgically fix user's real `templt.docx` → `template.docx`: unique slot ids per role/project, 3-paragraph for/content/endfor blocks, skills casing
- [x] Smoke-test docxtpl render with sample data — produces correct paragraph count per slot
- [x] Update template-config.yaml with real ids (ai_engineer / scada_engineer / resume_agent / rag) + counts (5/4/5/5)
- [x] Rewrite master.md: H2 headings tagged `[<slot_id>]`, real dates/companies, Mosaic→rag, Stitch→resume_agent, skeleton boilerplate stripped
- [x] Update writer + reviewer prompts with binding slot-mapping rule (find `[<id>]` heading or hard-fail)
- [x] Add underfill edge case: `bullet_count` is now an UPPER BOUND, writer can stop early to avoid padding
- [ ] First end-to-end run with a real JD <-- NEXT
- [ ] Decide on visual bullet styling in template.docx (`{{b}}` paragraph currently "Normal" — bullets won't render with bullet markers)

### Key Files (current shape)
**`master.md`** (POPULATED, ~7KB)
Real content for 4 sections, all H2 headings tagged `[ai_engineer]`, `[scada_engineer]`, `[rag]`, `[resume_agent]`. Skills inventory in 3 categories with dense tags. Single source of truth for every bullet the writer can produce.

**`template.docx`** (FIXED, 2.4MB)
User's polished resume with corrected docxtpl slots: 4 unique for/content/endfor blocks (one per role/project), skills placeholders cased correctly. `templt.docx` (typo source) kept as backup.

**`template-config.yaml`** (UPDATED)
4 slots: ai_engineer (5), scada_engineer (4), resume_agent (5), rag (5). Counts are now interpreted as upper bounds, not strict equality.

**`.claude/skills/resume-test/prompts/{writer,reviewer}.md`** (REVISED)
Writer: binding slot-mapping rule (search master.md for `[<id>]` heading), upper-bound count semantics with `underfilled` flag in output schema, hard early-stop triggers on padding/filler/repetition. Reviewer: count_violation only fires on over-cap or zero, underfill is a minor advisory.

**`scripts/setup.py`** (PATCHED)
`add_bullet_loop()` helper now emits 3 separate paragraphs (for / `{{b}}` / endfor). Future `--setup` runs won't reproduce the single-line bug.

### Decisions (active)
- **`[slot_id]` tags in H2 headings** — explicit binding from master.md sections to YAML slots. Writer hard-fails if a slot id has no matching `[<id>]` heading (no guessing from titles).
- **Bullet count is an UPPER BOUND** — writer produces 1..N, stops early to prevent hallucinated padding. Underfill surfaces as `<actual>/<bullet_count>` at the approval gate.
- **Mosaic = rag, Stitch = resume_agent** — slot id naming chosen for genericity (rag/resume_agent describe the type of artifact, not the project's branded name).

### Next Steps
1. Open Claude Code in this project, run `/resume-test`, paste a real JD.
2. Check `.tmp/<slug>/jd-analysis.json` after Stage 1 — verify standard ATS schema is populated correctly.
3. Check `.tmp/<slug>/bullets-v1.json` after Stage 2 — verify writer found `[<id>]` headings and produced sourced bullets.
4. Eyeball the rendered PDF — confirm visual bullets are how you want them. If they look like flat indented text instead of bulleted lines, change the `{{b}}` paragraph's style to "List Bullet" in Word.

### Blockers
None.

### Watch Out
- `{{b}}` content paragraph in `template.docx` is styled "Normal" (inherited from `templt.docx`). Generated bullets will render as flat text, not visually bulleted. Fix in Word if needed.
- docx2pdf opens Word in the foreground — close any open `template.docx` in Word before running the pipeline or save will fail.
- Stale lock file `~$mplate.docx` may persist if Word crashed; safe to delete manually if it blocks renders.

---
---

## Session Archive

### Session 2 — 2026-05-11: Real-content wiring + edge cases
**What we did:** Installed deps. Ran setup. Fixed user's real `templt.docx` (4 problems: shared slot ids, repeated for-loop paragraphs, skills casing, filename) — required two passes after discovering docxtpl needs separate paragraphs for for/content/endfor. Patched setup.py to never reproduce the single-line bug. Rewrote master.md with `[slot_id]` tagged headings + real career content. Updated writer/reviewer prompts to enforce the tag binding. Added upper-bound bullet count semantics with `underfilled` flag.
**Files:** template.docx, template-config.yaml, master.md, prompts/{writer,reviewer}.md, SKILL.md, scripts/setup.py, CLAUDE.md, PRD.md, .tmp/fix_template.py.
**Decisions:** Explicit `[slot_id]` tags over inferred mapping. Upper-bound counts over strict equality. Per-slot `underfilled: true` flag in writer output for transparency at approval gate.

### Session 1 — 2026-05-10: Initial design + scaffold
**What we did:** Walked the design tree via /grill-me (24 Qs). Built `.claude/skills/resume-test/`, slash command, three subagent prompts, fill_and_render.py + setup.py, project docs.
**Files:** SKILL.md, commands/resume-test.md, prompts/{analyzer,writer,reviewer}.md, scripts/{setup,fill_and_render}.py, CLAUDE.md, DEVLOG.md, PRD.md, requirements.txt.
**Decisions:** Skill + Task subagents over Python+SDK (no API spend, runs in Claude Code). File-based JSON handoff. Severity-tiered reviewer with 5 critical triggers. docx2pdf via Word.

---

## Milestones
- [x] Design locked
- [x] Skeleton scaffold complete
- [x] Real template + master.md wired in (slot ids match end-to-end)
- [x] Underfill edge case implemented
- [ ] First end-to-end successful run
- [ ] Pipeline used for a real job application
- [ ] Cover letter generation added (out of v1 scope)

## Mistakes & Lessons

### 2026-05-11 — docxtpl `{%p` requires separate paragraphs
**What happened:** First version of `setup.py` and `fix_template.py` placed the entire for-loop on one line: `{%p for b in X_bullets %}{{b}}{%p endfor %}`. docxtpl rendered the user's real .docx and threw `jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'endfor'.`
**Root cause:** The `{%p ... %}` suffix means "remove this paragraph at render time." Both for and endfor on one paragraph means jinja sees the for and endfor in the same compile unit but can't pair them with a content paragraph in between — there's no surviving content paragraph for the loop body to live in.
**How we fixed it:** Rewrote both scripts to emit THREE paragraphs per slot — `{%p for b in X_bullets %}`, `{{b}}` (the content paragraph that gets repeated), `{%p endfor %}`. Updated setup.py's `add_bullet_loop()` helper, the fix_template.py one-shot, and the docs (CLAUDE.md, setup.py print message). Smoke-tested with sample data — render succeeds, each slot produces the correct number of paragraphs.
**Lesson:** docxtpl's paragraph-level Jinja tags (`{%p`, `{%tr`, etc.) consume the entire containing paragraph. Loop bodies require their own paragraphs between the for and endfor tags. The single-line pattern is invalid even if it compiles textually.

## Technical Debt & Future Ideas
- `{{b}}` paragraphs in template.docx are styled "Normal" — bullets render as flat text. Need to apply "List Bullet" style in Word for visual bullet markers.
- LibreOffice headless fallback for users without Word.
- `/resume-test --cover-letter <folder>` (out of v1 scope).
- Multi-language support (currently English only).
- Optional: cache `.tmp/jd-analysis.json` keyed by JD hash so repeat runs of the same JD skip the analyzer.
- If breaking master.md sections into multi-paragraph sub-blocks (per-theme) becomes useful, the writer's source-scan would still work since it's section-bounded by H2.
