# Master Profile (example)

This file is a **template**. Copy it to `master.md` (gitignored) and replace
the placeholder content with your own career narrative. The writer agent
sources every bullet and skill from `master.md` — do not invent claims, if a
metric or technology isn't here it won't appear in any tailored resume.

```bash
cp master.example.md master.md
# then edit master.md with your real content
```

## Conventions

- Each role/project is an H2 section tagged with its slot id in literal
  square brackets, e.g. `## Role [senior_engineer]: ...`.
- Slot ids must match THREE things:
  1. `[<id>]` tag in master.md heading (here)
  2. `id:` entry in `template-config.yaml`
  3. `{%p for b in <id>_bullets %}` loop in `template.docx`
- Use dense prose. The writer extracts bullets per JD; more concrete claims
  give it more material to work with.
- Include exact metrics, named technologies, scope figures, and outcomes.
  Vague phrasing produces vague bullets.

---

## Role [senior_engineer]: Senior Software Engineer @ Example Corp (Jan 2024 – Present)

Replace this with a dense paragraph describing what you built and shipped at
this role. Include exact technologies, scale figures (RPS / users / GB),
specific outcomes, and named systems. Example shape:

"Built the X service from scratch in Go, handling ~500 RPS in production.
Cut p95 latency from 800ms to 120ms by introducing per-tenant caching with
Redis and connection pooling. Owned on-call rotation for the payments team
(8 engineers), reduced P1 incidents 40% through alerting cleanup and
runbook authoring. Led migration of 4 services to k8s on EKS. Mentored 2
junior engineers through promotion. Tech: Go, k8s, GitHub Actions, Postgres,
Redis, Kafka."

---

## Role [previous_role]: Previous Title @ Previous Company (Mar 2022 – Dec 2023)

Same shape — dense factual prose, real metrics, named tech. Older roles can
be slightly less detailed since they'll get fewer bullets in the YAML config.

---

## Project [main_project]: Main Project Name — One-Line Description

Dense paragraph about a notable project you've shipped. GitHub stars, user
count, scale, business impact, named tech stack — anything concrete you
might want to claim on a resume. If it's open source, link it; if it's
internal, describe the scope and outcome.

---

## Project [side_project]: Side Project Name — Description

Same shape. Side projects, hackathon wins, contributions to OSS — anything
that demonstrates skill or initiative.

---

## Skills Inventory

Three fixed categories. The writer picks/orders within each per JD relevance,
capped at `max_per_category` items from `template-config.yaml`. Only include
skills you genuinely have — the source-fidelity rule applies here too.

### Languages
Python, TypeScript, Go, SQL, Bash

### AI&ML
RAG, embeddings, vector search, prompt engineering, multi-agent orchestration,
hallucination mitigation, eval harnesses, ablation studies, PyTorch

### Concepts & Tools
FastAPI, Docker, Postgres, Redis, AWS, GitHub Actions, pytest, Git, REST APIs,
async/await
