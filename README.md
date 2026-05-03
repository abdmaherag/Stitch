# resume-tailor

A multi-agent Python pipeline that reads a job description and produces a tailored, ATS-optimized LaTeX resume — fully automated from paste to PDF-ready `.tex` file.

## How it works

```
master.md ──► master_parser
                │
JD text ──────► jd_analyzer  (Claude Sonnet)   → scratch/01-jd-analysis.json
                │
                ▼
              ranker          (pure Python)     → scratch/02a-ranked-bullets.json
                │  scores every bullet against 5 JD-derived signals
                ▼
              resume_selector (Claude Sonnet)   → scratch/02b-resume-selection.json
                │  picks bullets, light edits, skills line, summary
                ▼
              latex_editor    (pure Python)     → applications/{date}-{company}/Resume.tex
                │
                ▼
              tracker_manager (pure Python)     → applications/0tracker.csv
```

**master.md** is your bullet library — 8 bullets × 4 voices per topic, covering every experience and project. The pipeline never invents content; it only selects and lightly edits from what you wrote.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/resume-tailor.git
cd resume-tailor
pip install -e .
```

### 2. Add your resume data

```bash
cp master.example.md master.md
# Edit master.md — replace all placeholders with your actual bullets
```

```bash
cp template/template.example.tex template/template.tex
# Edit template/template.tex — fill in your name, contact info, frozen sections
```

Both files are gitignored. They never leave your machine.

### 3. Update anchors in latex_editor.py

Open `src/resume_tailor/subskills/latex_editor.py` and update the two constants at the top of the **USER CONFIG** section to match the exact text in your `template.tex`:

```python
MOSAIC_GITHUB_ANCHOR = r"\greylink{https://github.com/your-username/your-project}{GitHub} \\"
EDUCATION_ANCHOR     = r"\projectheading{Your University}"
```

These are used as string anchors to locate the regions to replace — they must match your template verbatim.

### 4. Set your API key

```bash
# Create resume-tailor/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Requires an [Anthropic API key](https://console.anthropic.com/) with credits. The pipeline calls Claude Sonnet twice per run (steps 1 and 2B).

### 5. Run

```bash
tailor
# or
python -m resume_tailor.main
```

Paste company name, role, JD link, then the full job description. Type `END` on its own line when done.

## Scoring weights (step 2A — ranker)

| Signal | Weight | What it checks |
|---|---|---|
| `anchor_match` | 30 | JD hard-requirement tech found in bullet |
| `keyword_overlap` | 25 | JD high-frequency terms found in bullet |
| `gap_relevance` | 20 | Bullet addresses a JD pain point |
| `has_metric` | 15 | Bullet contains a concrete number |
| `mirror_verb` | 10 | Opening verb matches a JD mirror verb |

## Bullet budget (default)

| Section | Bullets |
|---|---|
| AI Engineer (current role) | 2 |
| Mosaic project | 3 |
| Education | 1 |

Change in `ranker.py → SECTIONS`.

## State persistence

Each LLM step writes a scratch file. On the next run you are offered the option to skip already-completed steps — useful when a step fails mid-pipeline. Step 1's cache is hash-verified against the current JD; loading yesterday's analysis for today's job is blocked automatically.

## Project structure

```
src/resume_tailor/
  main.py               # REPL orchestrator
  client.py             # Anthropic client singleton
  prompts/              # System prompts (jd_analyzer, resume_selector)
  subskills/
    master_parser.py    # Parses master.md → structured dict at runtime
    jd_analyzer.py      # Step 1 — Claude call, extracts JD signals
    ranker.py           # Step 2A — pure Python scorer + budget allocator
    resume_selector.py  # Step 2B — Claude call, selection + light editing
    latex_editor.py     # Step 3 — pure Python template filler
    tracker_manager.py  # Step 4 — CSV appender
tools/
  bullet_generator.py   # Authoring tool — generates master.md bullets from paragraphs
template/
  template.example.tex  # Public placeholder template (fill in and rename)
master.example.md       # Public placeholder bullet library (fill in and rename)
```

## Known limitations / TODO

- **B3 — validator retry loop**: on a bad 2B response the pipeline retries once. If the retry also fails, it raises and the scratch is not written — you have to re-run from 2B manually.
- **B4 — SCADA / second-role block**: the LaTeX editor has a frozen SCADA block for a second role. If your second role is different, you need to edit `latex_editor.py → _FROZEN_SCADA` and the corresponding template block.
- Model name `claude-sonnet-4-5` — verify this matches your account's available models on the [Anthropic console](https://console.anthropic.com/). If not, update `MODEL` in `subskills/jd_analyzer.py` and `subskills/resume_selector.py`.

## Requirements

- Python 3.11+
- `anthropic` SDK
- `python-dotenv`
- A LaTeX installation (e.g. TeX Live, MiKTeX) to compile the output `.tex` to PDF

## License

MIT
