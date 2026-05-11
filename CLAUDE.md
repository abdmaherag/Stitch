# resume-test

Personal resume tailoring pipeline. Three Claude subagents (analyzer / writer / reviewer) tailor bullets and skills from `master.md` to a pasted JD, fill a fixed `template.docx`, and render PDF via Word.

## Stack

- Python 3.11+ (docxtpl, docx2pdf, python-docx, PyYAML)
- Microsoft Word (required for docx2pdf)
- Claude Code skills + Task subagents (Sonnet 4.6 for analyzer/reviewer, Opus 4.7 for writer)

## Commands

- `/resume-test`                       — run the full pipeline (paste JD when prompted)
- `/resume-test --setup`               — scaffold master.md, template-config.yaml, placeholder template.docx

## Structure

```
.claude/
  skills/resume-test/
    SKILL.md            # orchestrator — controls pipeline stages
    prompts/
      analyzer.md       # Sonnet — extracts standard ATS schema from JD
      writer.md         # Opus   — produces bullets + skills from master.md
      reviewer.md       # Sonnet — audits against master.md, emits severity-tiered issues
  commands/
    resume-test.md      # slash command entry point
master.md               # SOURCE OF TRUTH for all bullets and skills
template.docx           # polished resume with Jinja slots (docxtpl)
template-config.yaml    # per-role bullet counts, skill categories
scripts/
  setup.py              # first-run scaffolding
  fill_and_render.py    # docxtpl fill + Word PDF render
.tmp/<company-slug>/    # per-company pipeline artifacts (jd-raw.txt, jd-analysis.json,
                        # bullets-v[1,2].json, review-v[1,2].json) — gitignored,
                        # one folder per company so concurrent runs don't overwrite
out/<company>-<date>/   # final resume.docx, resume.pdf, bullets.json, jd.txt
requirements.txt
```

## Architecture

Linear 3-stage pipeline orchestrated by `SKILL.md`. Stage 0 asks for the company name and slugifies it (`<slug>`); all subsequent artifacts live under `.tmp/<slug>/` so concurrent runs for different companies never overwrite each other. Subagents communicate via JSON files in that folder — parent Claude passes file paths only, never inline content. Reviewer flags issues with severity tiers; only `critical` issues trigger a single writer revision pass. After (optional) revision, parent prints final bullets + skills + reviewer notes and gates on user approval before invoking `scripts/fill_and_render.py` for the PDF.

## Conventions

- **Source fidelity is absolute** — writer cannot invent metrics, tech, or scope not present in `master.md`. Reviewer's `fabrication` check is the strictest gate.
- **Bullets-only + skills-only tailoring** — name, contact, role titles, dates, project names, links, education are static in `template.docx`.
- **Skills: 3 fixed categories** — `Languages`, `AI&ML`, `Concepts & Tools`.
- **Bullet counts are fixed per role** in `template-config.yaml`. Mismatches are reported as a minor `numbering` issue (no auto-revise loop). Only invalid IDs trigger critical `count_violation`.
- **docxtpl slot syntax** — bullet lists need THREE paragraphs: `{%p for b in <id>_bullets %}` / `{{b}}` (List Bullet style) / `{%p endfor %}`. The for/content/endfor on one line is a Jinja syntax error.
- **One folder per run** in `out/<company>-<YYYY-MM-DD>/`.
