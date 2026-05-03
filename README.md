# Stitch

A multi-agent pipeline that reads a job description and produces a tailored, ATS-optimized LaTeX resume — automatically selecting, scoring, and lightly editing bullets from your personal library to match each role.

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

**stitch.yaml** is your personal config — it tells the pipeline which sections you have, how many bullets each gets, and where they live in your LaTeX template. No code changes needed to adapt this to your own background.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/abdmaherag/Stitch.git
cd Stitch
pip install -e .
```

### 2. Add your resume data

```bash
cp master.example.md master.md
# Edit master.md — replace all placeholders with your actual bullets
```

```bash
cp template/template.example.tex template/template.tex
# Edit template/template.tex — fill in your name, contact info, and section layout
```

### 3. Configure your sections

```bash
cp stitch.example.yaml stitch.yaml
# Edit stitch.yaml — define your sections, bullet budgets, and template anchors
```

Each entry in `stitch.yaml` maps one block in `master.md` to one block in `template.tex`:

```yaml
sections:
  - key: current_role
    master_label: "My Current Role"   # substring of the ### header in master.md
    master_section: experience
    master_slug: role1
    budget: 2                         # bullets to select for this section
    max_topics: 2
    min_score_pct: 0.65
    template_anchor: '\projectheading{My Current Role Title}'  # exact string in template.tex

  - key: main_project
    master_label: "My Main Project"
    master_section: projects
    master_slug: proj1
    budget: 3
    max_topics: 2
    min_score_pct: 0.65
    template_anchor: '\projectheading{My Project Name}'
    github_anchor: '\greylink{https://github.com/your-username/your-project}{GitHub} \\'
    frozen_techstack: 'FastAPI | PostgreSQL | React | Docker'
```

All three files (`master.md`, `template.tex`, `stitch.yaml`) are gitignored — they never leave your machine.

### 4. Set your API key

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Requires an [Anthropic API key](https://console.anthropic.com/) with credits. The pipeline makes two Claude calls per run (JD analysis and bullet selection).

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

## Bullet budget

Defined per section in `stitch.yaml`. Add as many sections as your resume has — the pipeline handles any number.

## State persistence

Each LLM step writes a scratch file. On the next run you are offered the option to skip already-completed steps — useful when a step fails mid-pipeline. Step 1's cache is hash-verified against the current JD; loading a cached analysis for a different job is blocked automatically.

## Project structure

```
src/resume_tailor/
  main.py               # REPL orchestrator
  client.py             # Anthropic client singleton
  config.py             # Loads stitch.yaml and serves it to the pipeline
  prompts/              # System prompts (jd_analyzer, resume_selector)
  subskills/
    master_parser.py    # Parses master.md → structured dict at runtime
    jd_analyzer.py      # Step 1 — Claude call, extracts JD signals
    ranker.py           # Step 2A — pure Python scorer + budget allocator
    resume_selector.py  # Step 2B — Claude call, selection + light editing
    latex_editor.py     # Step 3 — pure Python template filler
    tracker_manager.py  # Step 4 — CSV appender
tools/
  bullet_generator.py   # Authoring tool — generates master.md bullets from raw paragraphs
template/
  template.example.tex  # Placeholder LaTeX template (copy, rename, fill in)
master.example.md       # Placeholder bullet library (copy, rename, fill in)
stitch.example.yaml     # Placeholder section config (copy, rename, fill in)
```

## Known limitations

- **Validator retry**: on a failed 2B response the pipeline retries once with the exact errors fed back to Claude. If the retry also fails, it raises — re-run from 2B using the scratch file cache.
- **Model name**: `claude-sonnet-4-5` — verify this matches your account's available models on the [Anthropic console](https://console.anthropic.com/). If not, update `MODEL` in `subskills/jd_analyzer.py` and `subskills/resume_selector.py`.

## Requirements

- Python 3.11+
- `anthropic`, `python-dotenv`, `pyyaml`
- A LaTeX installation (e.g. TeX Live, MiKTeX) to compile the output `.tex` to PDF

## License

MIT
