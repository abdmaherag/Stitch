# stitch Dev Log

> Originally built as "resume-test" through Sessions 1-3. Renamed to "stitch"
> in Session 4 (folder, package, skill, slash command, docs all renamed end-to-end).
> Older archive entries below reference the old names (`resume_test` package,
> `/resume-test` skill, `.claude/skills/resume-test/`) as factual history.

## Working State
**Session:** 4 | **Date:** 2026-05-12 | **Branch:** main

### Active Task
Standalone Python port shipped on `OPTIONC` branch. Project is now runnable two ways: via Claude Code skill (main branch design) OR via direct Anthropic SDK (`python -m resume_test`). All prompts, configs, and renderer shared between the two modes — only the orchestration layer differs.

- [x] git init + commit baseline on main (Claude Code skill version, sans personal data)
- [x] Create OPTIONC branch
- [x] Build `src/resume_test/` package: pipeline, stages, anthropic_client, slugify, cli, __main__
- [x] Add pyproject.toml with `resume-test` console script entry point
- [x] Add `anthropic>=0.40.0` to requirements.txt
- [x] pytest suite (33 tests, all passing): slugify normalization, JSON-extraction lenient parsing + retry, fill_and_render slot validation, has_critical_issues branching
- [x] Eval scripts: `eval/atom_grounding.py` (verbatim atom check vs master.md, target ≥95%), `eval/jd_coverage.py` (required-skill substring check, target ≥80%)
- [x] Sample JD fixture for eval reproducibility
- [x] README.md with mermaid architecture diagram, install, dual-mode docs, eval usage, project layout, stack rationale
- [x] LICENSE (MIT)
- [x] gitignore personal data (master.md, template.docx, templt.docx, ~$*.docx) so portfolio repo never leaks contact info
- [ ] First end-to-end run with real JD via standalone CLI <-- NEXT
- [ ] Decide: merge OPTIONC → main, or keep as a parallel branch

### Key Files (current shape)
**`src/resume_test/pipeline.py`** (NEW, ~140 lines)
6-stage orchestrator. Standalone equivalent of SKILL.md. Slugify → save JD raw → analyzer (Sonnet) → writer pass 1 (Opus) → reviewer pass 1 (Sonnet) → conditional revision (writer pass 2 + reviewer pass 2 informational, only if any critical issue) → CLI approval gate → subprocess to fill_and_render.py.

**`src/resume_test/anthropic_client.py`** (NEW, ~95 lines)
SDK wrapper. `Stage` dataclass (model + system_prompt + max_tokens). `call()` does the API call with `cache_control: ephemeral` on the system prompt for ~90% input-cost reduction on cache hits. `call_json()` parses, strips code fences, retries once with explicit reminder on parse failure, raises RuntimeError after second failure.

**`src/resume_test/stages.py`** (NEW, ~115 lines)
Per-stage helpers: `run_analyzer`, `run_writer` (handles both first pass and revision pass with optional `previous_bullets` + `review` args), `run_reviewer`. Each loads prompt from `.claude/skills/resume-test/prompts/`, builds user message with XML-tagged context blocks, writes JSON output to `.tmp/<slug>/`. Plus `has_critical_issues()` for the revision-loop decision.

**`src/resume_test/slugify.py`** (NEW, ~30 lines)
Pure helper: company name → filesystem-safe slug. Unicode normalization → ASCII → lowercase → collapse non-alphanumeric to single hyphens → strip. 12 parametrized tests cover Unicode, punctuation, edge cases.

**`pyproject.toml`** (NEW)
Setuptools config. `resume-test` console script entry point. `[dev]` extra has pytest + pytest-mock. `pythonpath = ["src"]` so tests resolve the package without install.

**`eval/atom_grounding.py`** (NEW, ~120 lines)
Extracts numbers + tech tokens (CamelCase, ALL_CAPS, hyphenated) from each bullet via two regexes, checks each appears verbatim in master.md (case-insensitive substring). Score = grounded / total. Stop-list filters out the verb whitelist so "Built" doesn't get flagged as a tech atom.

### Decisions (active)
- **Dual-mode by design:** prompts + configs + renderer shared between Claude Code skill (.claude/skills/resume-test/) and standalone Python (src/resume_test/). Only the orchestrator differs. Anyone can run either path; same outputs.
- **Personal data gitignored from day one:** master.md, template.docx, templt.docx never enter git history. Setup script generates skeletons; users customize locally.
- **Prompt caching on system messages:** the analyzer/writer/reviewer prompts are large and reused — `cache_control: ephemeral` on each system message means subsequent calls within 5 minutes hit cache.
- **JSON retry, not validate-and-fail:** if the model wraps output in code fences or emits invalid JSON, we strip fences and retry once with an explicit reminder. Two failures → RuntimeError with the raw output for debugging.
- **Eval scripts ship as artifacts, not gates:** `eval/atom_grounding.py` and `eval/jd_coverage.py` are runnable but not wired into the pipeline. They document what "good output" means objectively, give recruiters reading the repo something concrete to point to, and let me run regression checks when changing prompts.

### Next Steps
1. Run end-to-end via standalone CLI: `export ANTHROPIC_API_KEY=...` then `python -m resume_test --company "Acme" --jd ./test-jd.txt`. Verify the full 6 stages execute against the real Anthropic API.
2. Run the eval scripts on the resulting bullets-v1.json — confirm atom-grounding ≥95% and JD coverage ≥80% on a real run.
3. If both work, decide whether to merge OPTIONC → main or keep as a parallel "standalone" branch with main being "Claude Code only."
4. Push to GitHub. Pin Mosaic + AI Engineer + resume-test as the three portfolio entries.

### Blockers
None.

### Watch Out
- Standalone mode requires `ANTHROPIC_API_KEY` env var. Costs ~$0.06–0.15 per pipeline run depending on revision-pass triggering (Sonnet ~$0.012/call, Opus ~$0.045/call, prompt cache helps).
- Subprocess call to `fill_and_render.py` from `pipeline.py` uses `sys.executable` — should work in venvs. Check stderr if rendering fails.
- pyproject.toml uses src-layout; `pip install -e .` is required for `resume-test` console script to work, OR set PYTHONPATH=src for direct invocation.

---
---

## Session Archive

### Session 3 — 2026-05-11: OPTIONC standalone port (portfolio-ize)
**What we did:** git init. Committed Claude Code skill as baseline on main. Created OPTIONC branch. Ported the orchestrator off Claude Code: built `src/resume_test/` (pipeline, stages, anthropic_client, slugify, cli, __main__) using the Anthropic SDK directly, with prompt caching + JSON-extraction + one-shot retry. Added pyproject.toml + console script entry. Wrote 33 pytests (all passing). Built two eval scripts (atom_grounding, jd_coverage) + sample JD fixture. Wrote README with mermaid architecture diagram + install + dual-mode docs. Added MIT license. Gitignored personal data.
**Files:** src/resume_test/{__init__,pipeline,stages,anthropic_client,slugify,cli,__main__}.py, tests/{test_slugify,test_anthropic_client,test_fill_and_render,test_stages}.py, eval/{atom_grounding,jd_coverage,fixtures/sample-jd-ai-engineer.txt}, pyproject.toml, requirements.txt, README.md, LICENSE, .gitignore (updated).
**Decisions:** Dual-mode (Claude Code AND standalone) over migrating fully off Claude Code. Personal data gitignored from initial commit so portfolio repo never leaks contact info. Prompt caching on every system message. JSON retry over validate-and-fail.

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
- [x] Standalone Python port shipped (OPTIONC branch)
- [x] Test suite (33 tests, all passing)
- [x] Eval scripts (atom_grounding + jd_coverage)
- [x] README + LICENSE + portfolio-ready packaging
- [ ] First end-to-end successful run via standalone CLI
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
- 60-second screencap of standalone CLI for the README.
