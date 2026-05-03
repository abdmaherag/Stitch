# Master Resume Source

This file is the source of truth for resume tailoring. Each project has:
- A **dense paragraph** (raw material — fallback for cross-cutting Job Descriptions)
- **Topic groups** filtered to AI-engineering-relevant work
- Per topic: **8 bullets** (2 each in Results-Oriented / Architectural Focus / Concise & Punchy / Highly Engineered)

The tailoring skill picks the topic(s) matching the Job Description, then selects the top N bullets by keyword density and voice fit.

---

## Experience

### AI Engineer (Current)

_~N months, ongoing. Solo._

**Dense paragraph:** [Raw wall of text describing everything you did — no bullet formatting. Used as fallback context for the LLM and for cross-cutting JDs. Include tech stack, scale, architecture decisions, and measurable outcomes.]

#### Topic: [Topic Name, e.g. "Email RAG System"]

- [Results-Oriented bullet — what shipped and what it solved for users.] (Results-Oriented)
- [Results-Oriented bullet — concrete outcome, user-facing win.] (Results-Oriented)
- [Architectural Focus bullet — design decision and why it was made.] (Architectural Focus)
- [Architectural Focus bullet — system shape, component boundaries.] (Architectural Focus)
- [Concise & Punchy bullet — short, high-signal, verb-first.] (Concise & Punchy)
- [Concise & Punchy bullet — distilled to one strong claim.] (Concise & Punchy)
- [Highly Engineered bullet — specific implementation detail, metric, or algorithm.] (Highly Engineered)
- [Highly Engineered bullet — shows depth of craft.] (Highly Engineered)

#### Topic: [Topic Name, e.g. "AI Chatbot"]

- [Results-Oriented bullet] (Results-Oriented)
- [Results-Oriented bullet] (Results-Oriented)
- [Architectural Focus bullet] (Architectural Focus)
- [Architectural Focus bullet] (Architectural Focus)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Highly Engineered bullet] (Highly Engineered)
- [Highly Engineered bullet] (Highly Engineered)

---

### Previous Role (e.g. "Full-Stack Developer")

_Mon YYYY – Mon YYYY. [Team size, context]._

**Dense paragraph:** [Raw description of the role.]

#### Topic: [Topic Name]

- [Results-Oriented bullet] (Results-Oriented)
- [Results-Oriented bullet] (Results-Oriented)
- [Architectural Focus bullet] (Architectural Focus)
- [Architectural Focus bullet] (Architectural Focus)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Highly Engineered bullet] (Highly Engineered)
- [Highly Engineered bullet] (Highly Engineered)

---

## Projects

### [Project Name, e.g. "Mosaic RAG Pipeline"]

**Dense paragraph:** [Raw description of the project — architecture, stack, scale, what you built and why.]

#### Topic: [Topic Name, e.g. "RAG / Retrieval"]

- [Results-Oriented bullet] (Results-Oriented)
- [Results-Oriented bullet] (Results-Oriented)
- [Architectural Focus bullet] (Architectural Focus)
- [Architectural Focus bullet] (Architectural Focus)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Highly Engineered bullet] (Highly Engineered)
- [Highly Engineered bullet] (Highly Engineered)

---

## Education

### [University Name]

**Degree:** [B.S. / M.S.] in [Field] | [YYYY – YYYY]

**Graduation Project:** [Project Title] | [Tech stack]

#### Topic: [Topic Name, e.g. "ML / Graduation Project"]

- [Results-Oriented bullet] (Results-Oriented)
- [Results-Oriented bullet] (Results-Oriented)
- [Architectural Focus bullet] (Architectural Focus)
- [Architectural Focus bullet] (Architectural Focus)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Concise & Punchy bullet] (Concise & Punchy)
- [Highly Engineered bullet] (Highly Engineered)
- [Highly Engineered bullet] (Highly Engineered)

---

## Skills

```
AI & ML: [comma-separated list of AI/ML technologies — sorted by recency/relevance]
Concepts & Tools: [comma-separated list — frameworks, infra, paradigms]
Languages: [Python, JavaScript, TypeScript, SQL, ...]
```

---

## Notes on Format

- Voice labels must be exactly one of: `Results-Oriented`, `Architectural Focus`, `Concise & Punchy`, `Highly Engineered`
- 2 bullets per voice per topic (8 total per topic)
- Each bullet ≤ 200 chars (bold markers excluded from count)
- Topic names must match slugs expected by `ranker.py` — see `TOPIC_SLUGS` in `master_parser.py`
- Dense paragraphs are used by the ranker as fallback signal — write them as one long paragraph, not bullets
