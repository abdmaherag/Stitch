# resume-tailor

Multi-agent Python pipeline that tailors a LaTeX resume to a job description.
master.md is the bullet library. template/template.tex is the locked layout.

## Stack

- Python 3.11+
- anthropic SDK (Claude Sonnet 4.5)
- python-dotenv

## Commands

```
pip install -e .
tailor                        # run the full pipeline (REPL)
python -m resume_tailor.main  # same
```

## Structure

```
src/resume_tailor/
  main.py               # REPL orchestrator — runs steps 1 → 2A → 2B → 3 → 4
  client.py             # Anthropic singleton
  prompts/
    jd_analyzer.py      # Step 1 system prompt
    resume_selector.py  # Step 2B system prompt
  subskills/
    master_parser.py    # Parses master.md → structured dict at runtime
    jd_analyzer.py      # Step 1 — Claude call, extracts JD signal
    ranker.py           # Step 2A — pure Python bullet scorer + topic allocator
    resume_selector.py  # Step 2B — Claude call, final selection + light editing
    latex_editor.py     # Step 3 — pure Python template filler
    tracker_manager.py  # Step 4 — pure Python CSV appender
tools/
  bullet_generator.py   # Authoring tool (NOT pipeline) — generates master.md bullets from dense paragraphs
scratch/                # debug output from each step (gitignored)
applications/           # output resumes + 0tracker.csv
template/template.tex   # locked LaTeX layout — DO NOT EDIT structure
master.md               # bullet library — source of truth (8 bullets × 4 voices per topic)
```

## Pipeline

```
master.md ──► master_parser
                │
JD text ──────► jd_analyzer (Sonnet)  ──► scratch/01-jd-analysis.json
                │
                ▼
              ranker (Python)          ──► scratch/02a-ranked-bullets.json
                │  scores every bullet, allocates budget per topic
                ▼
              resume_selector (Sonnet) ──► scratch/02b-resume-selection.json
                │  picks bullets, light edits, skills, summary
                ▼
              latex_editor (Python)    ──► applications/{date}-{company}/Resume.tex
                │
                ▼
              tracker_manager (Python) ──► applications/0tracker.csv
```

## Key Rules

- Bullet budget: AI Engineer 2, Mosaic 3, Education 1 (total 6)
- Every bullet ≤ 200 chars (bold markers excluded from count)
- Skills lines ≤ 200 chars each. Summary ≤ 200 chars.
- Mosaic techstack line is frozen — never edited by the pipeline
- SCADA block in template is frozen — never edited by the pipeline
- master.md is the only source of bullets — 2B may not invent content

## Scoring Weights (ranker.py)

```
anchor_match    30  # JD must-have tech found in bullet
keyword_overlap 25  # JD frequency terms found in bullet
gap_relevance   20  # bullet addresses a the_gap pain point
has_metric      15  # bullet contains a concrete number
mirror_verb     10  # opening verb matches a JD mirror_verb
```

## State Persistence

Scratch files survive between runs. main.py offers to load each step from its
scratch file so you can resume after a 2B failure without re-paying step 1/2A.

## Environment

Requires `resume-tailor/.env`:
- `ANTHROPIC_API_KEY` — Anthropic API key
