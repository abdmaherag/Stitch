---
description: Tailor resume to a job description via 3-agent pipeline (analyzer / writer / reviewer)
argument-hint: [--setup | --rerender <output-folder>]
---

Invoke the `resume-test` skill. Arguments: $ARGUMENTS

Modes:
- (no args)              — run the full pipeline (analyzer → writer → reviewer → render)
- `--setup`              — scaffold master.md, template-config.yaml, placeholder template.docx
- `--rerender <folder>`  — re-fill template.docx and re-render PDF from `<folder>/bullets.json` without calling any LLM

Follow the SKILL.md exactly. Use Task subagents for analyzer/writer/reviewer with the model assignments specified there. Pass file paths to subagents, never inline content.
