# PRD — resume-test

## Problem

Tailoring a resume for each job application is time-consuming and error-prone. Generic AI resume tools either (a) rewrite content the user never produced (hallucinated metrics, fake tech) or (b) lose the user's polished .docx formatting. Existing personal master profiles aren't directly usable — they need extraction, JD-aware selection, and ATS keyword weaving per application.

## Goal

A Claude Code skill that, on `/resume-test`, takes a pasted JD and produces a tailored .docx + PDF in under ~2 minutes, with bullets sourced strictly from a personal `master.md`, in the user's existing polished template, with reviewer-checked accuracy.

## Non-goals (v1)

- Scalability beyond personal use (one user, one master.md, one template).
- Cover letter generation (deferred to a separate command).
- Multi-language / locale support.
- LibreOffice fallback for PDF conversion (Word is assumed installed).
- Auto-pulling JDs from URLs / job board APIs.
- Web UI or non-Claude-Code interface.

## Users

One: the project owner. All design tradeoffs assume single-user, personal workflow.

## Requirements

### Functional

1. **Triggered via `/resume-test`** slash command in Claude Code.
2. **JD input** by paste in the next message after the trigger (no URL/file argument). The orchestrator first asks for the company name (slugified into `<slug>`) before asking for the JD, then saves the JD and all subsequent artifacts to `.tmp/<slug>/` so per-company runs are isolated.
3. **Three-stage pipeline:**
   - Analyzer (Sonnet 4.6) — extracts standard ATS schema from JD.
   - Writer (Opus 4.7) — produces per-role bullets and categorized skills, sourced from master.md.
   - Reviewer (Sonnet 4.6) — audits writer output for fabrication, wrong attribution, miscategorization, count violations, and JD irrelevance.
4. **Severity-tiered reviewer:**
   - `critical` issues trigger one writer revision pass.
   - `minor` issues are reported but do not loop.
5. **Approval gate** before PDF rendering. User can request bullet tweaks; writer revises without invoking the reviewer.
6. **Output:** `out/<company-slug>-<YYYY-MM-DD>/` containing `resume.docx`, `resume.pdf`, `bullets.json`, `jd.txt`. Never overwrites past runs.
7. **Auxiliary commands:**
   - `--setup` scaffolds `master.md`, `template-config.yaml`, placeholder `template.docx` (refuses to overwrite).
   - `--rerender <folder>` re-fills + re-renders PDF from an edited `bullets.json` without invoking any LLM.

### Constraints

- **Source fidelity** — every bullet must be backed by claims in `master.md` for the corresponding role/project. No invented metrics or technologies.
- **Bullets and skills only** — name, contact info, role titles, companies, dates, project names, links, education are static in `template.docx`.
- **Fixed bullet counts** per role/project, defined in `template-config.yaml`. Writer must match exactly.
- **3 fixed skill categories:** Languages, AI&ML, Concepts & Tools.
- **File-based handoff** — every subagent communicates via JSON files under `.tmp/<company-slug>/`; parent Claude passes paths, not content. The slug is captured at Stage 0 (user-typed company name, slugified) so concurrent runs for different companies cannot overwrite each other.

### Quality

- Pipeline run completes in ≤ 2 minutes (analyzer + writer + reviewer + render) on a typical JD.
- Reviewer catches obvious fabrications (e.g., invented numerical metrics) before render in ≥ 95% of cases.
- Generated PDF visually matches what the user sees opening the filled .docx in Word (docx2pdf via Word COM).

## Success criteria

- User runs `/resume-test`, pastes a JD, approves at the gate, gets a usable `resume.pdf` in their `out/` folder — without manually editing the .docx.
- Reviewer's `bullet_issues` array is empty after the (optional) revision pass for ≥ 80% of runs on common JDs.
- User adopts the pipeline as their default for job applications.

## Out of scope, deferred

- Cover letter generation as `/resume-test --cover-letter <folder>` (post-v1).
- Hash-based analyzer cache for repeat JDs.
- LibreOffice headless mode.
- Web UI / hosted version.
