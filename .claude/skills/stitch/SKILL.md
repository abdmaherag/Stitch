---
name: stitch
description: Tailor a resume to a specific job description via a 3-agent pipeline (analyzer / writer / reviewer). Sources bullets from master.md, fill a fixed .docx template, render PDF. Trigger on "/stitch".
user-invocable: true
---

# stitch

**Source of truth:** `master.md` (H2 sections per role/project + Skills Inventory)
**Template:** `template.docx` (Jinja slots via docxtpl, populated by `scripts/fill_and_render.py`)
**Slots config:** `template-config.yaml` (per-role bullet counts + 3 skill categories)

---

## Modes

The orchestrator parses arguments and routes to one of three modes.

### Mode A — Main pipeline (no args)

Run the full analyzer → writer → reviewer → render pipeline.

### Mode B — Setup (`--setup`)

Run `python scripts/setup.py` to scaffold `master.md`, `template-config.yaml`, and a placeholder `template.docx`. Refuses to overwrite existing files. Print the script's output and stop.

---

## Mode A — Pipeline

### Stage 0 — Resolve JD

Ask the user: **"Comapny name."**

Create directory `.tmp/<company>/`.

Ask the user: **"Paste the job description text."**

Save the JD text to `.tmp/<company>/jd-raw.txt`.

### Stage 1 — Analyzer subagent (Sonnet 4.6)

Spawn a Task subagent with:
- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `JD analyzer`
- `prompt`: contents of `.claude/skills/stitch/prompts/analyzer.md`.

### Stage 2 — Writer subagent (Opus 4.7)

Spawn a Task subagent with:
- `subagent_type`: `general-purpose`
- `model`: `opus`
- `description`: `Resume writer (pass 1)`
- `prompt`: contents of `prompts/writer.md`

### Stage 3 — Reviewer subagent (Sonnet 4.6)

Spawn a Task subagent with:
- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `Resume reviewer (pass 1)`
- `prompt`: contents of `prompts/reviewer.md` plus:

### Stage 4 — Conditional revision

Read `.tmp/<company>/review-v1.json`. Look at `bullet_issues[]`.

- **If any issue has `severity: "critical"`** → spawn writer again with these additional inputs documented:
  ```
  Inputs:
    previous inputs
    .tmp/<company>/bullets-v1.json   (previous attempt — revise this)
    .tmp/<company>/review-v1.json    (issues to fix; address every "critical" item)

  Output: .tmp/<company>/bullets-v2.json
  ```

  Then spawn reviewer once more on `.tmp/<comapny>/bullets-v2.json` → `.tmp/<company>/review-v2.json` (informational; do **not** loop again regardless of verdict).
  Set `bullets-final = .tmp/<company>/bullets-v2.json`, `review-final = .tmp/<company>/review-v2.json`.

- **Else (no critical issues)** → set `bullets-final = .tmp/<company>/bullets-v1.json`, `review-final = .tmp/<company>/review-v1.json`. Skip the second writer pass.

### Stage 5 — Approval gate

Read `bullets-final` and `review-final`. Print to user:

```
## Tailored bullets

### <role_id 1> (<bullet_count> bullets)
1. ...
2. ...
...

### <project_id 1> (<bullet_count> bullets)
1. ...
...

## Skills
- Languages:        ...
- AI&ML:            ...
- Concepts & Tools: ...

## Reviewer notes
- [minor] ...
- [minor] ...
(any remaining critical issues from pass 2 listed here too)
```

Then ask: **"Approve to render PDF? (yes / change <description>)"**

- If user says yes/approve/ship → Stage 6.
- If user requests changes → spawn writer once more (Opus) with their feedback embedded in the prompt, write `.tmp/<slug>/bullets-final.json` (overwrite), re-print, ask again. No reviewer call on user-driven revisions.

### Stage 6 — Render

Use `<company>` from Stage 0 and today's date (YYYY-MM-DD).

Output folder: `out/<company>-<YYYY-MM-DD>/`

Run:
```
python scripts/fill_and_render.py \
  --bullets <bullets-final path> \
  --jd .tmp/<company>/jd-raw.txt \
  --out out/<company>-<YYYY-MM-DD>/
```
Print the output folder path and the file list. Done.

---

## Subagent invocation contract

Every subagent call follows the same shape:

1. Subagents receive **file paths**, never inline content. They use Read to load inputs.
2. Subagents write outputs to specified paths.
3. Subagents return only a confirmation line (e.g., `Wrote .tmp/<company>/jd-analysis.json with 7 required skills, 4 preferred.`).
4. Parent never holds large content in memory — passes paths and reads files only when needed for a decision.

## Failure modes to handle

- **JSON parse error from subagent output:** print the bad file path, ask user to inspect, halt.
- **`scripts/fill_and_render.py` non-zero exit:** print stderr verbatim, halt. Do not attempt to fix the .docx programmatically.
