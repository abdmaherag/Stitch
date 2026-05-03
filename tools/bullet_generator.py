"""
Bullet Generator — one-time authoring tool, NOT part of the tailoring pipeline.

Usage:
    python tools/bullet_generator.py

Interactive REPL:
  1. Paste or reference a dense paragraph for your project/experience.
  2. List the topics you want bullets for.
  3. Claude generates 8 voice-labeled bullets per topic in master.md format.
  4. Review, edit, then paste into master.md.

Why this exists:
  Writing 8 bullets × 4 voices per topic manually is slow and inconsistent.
  This script generates structured drafts from raw paragraph material.
  YOU commit the final content — the generator is a drafting aid, not an oracle.

Output format matches master.md exactly so you can paste directly.
"""
import sys
from pathlib import Path

# Allow running from project root without installing the package
_PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from resume_tailor.client import get_client  # noqa: E402

MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """You are an expert resume bullet writer specialising in AI/ML engineering roles.

Given a dense technical paragraph and a list of topics, you generate resume bullets
in exactly the format below. Your output will be pasted directly into a master.md
resume bullet library — precision and format compliance are critical.

## Voice styles (exactly these 4, exactly 2 bullets each per topic)

Results-Oriented     Lead with a measurable outcome, business value, or quantified improvement.
                     Numbers and impact first. E.g. "Reduced X by Y%...", "Achieved Z...".

Architectural Focus  Lead with a design decision, system structure choice, or technical tradeoff.
                     Frame as "Architected / Designed / Structured...".

Concise & Punchy     Short, direct. 1–2 tight clauses. Action verb + the sharpest specific detail.
                     No hedging. No filler. Maximum signal per word.

Highly Engineered    Lead with the precise technical mechanism: the specific parameter, algorithm,
                     data structure, or implementation detail that makes this non-trivial.

## Output rules

- Exactly 8 bullets per topic: 2 per voice in order (RO, AF, CP, HE)
- Each bullet ≤ 200 characters (bold markers **like this** excluded from count)
- Begin every bullet with a strong action verb (never "I" or a noun)
- Bold (**word**) the single most JD-relevant technical term in the bullet
- No bullet may repeat a concrete fact already stated in another bullet for this topic
- Format each bullet as:  - [text] ([Voice Label])
- Separate topics with a blank line; include the #### Topic: header

## Example output for one topic

#### Topic: Hybrid Retrieval

- Reduced query latency 40% by replacing vector-only search with **hybrid retrieval** fusing BM25 and cosine similarity via Reciprocal Rank Fusion. (Results-Oriented)
- Achieved 100% hit@5 on a 2,781-chunk eval corpus by combining **ChromaDB** HNSW cosine search with rank-bm25 BM25Okapi at the canonical k=60 constant. (Results-Oriented)
- Architected **hybrid retrieval** to fuse vector and lexical signals, fetching 2× top-k from each retriever before RRF fusion to maximise candidate diversity. (Architectural Focus)
- Designed per-source filter logic separating cosine gates for vector hits from zero-score gates for BM25 hits, preserving **hallucination guards** under true hybrid operation. (Architectural Focus)
- Built **hybrid retrieval** fusing ChromaDB cosine search and BM25Okapi via RRF, eliminating pure-vector recall gaps on keyword-heavy queries. (Concise & Punchy)
- Replaced API-priced embeddings with **sentence-transformers** all-MiniLM-L6-v2 (384-dim, CPU-only), eliminating per-ingest embedding cost entirely. (Concise & Punchy)
- Implemented **BM25 index caching** per device with dirty-bit invalidation on upload/delete, avoiding full corpus re-tokenization on every query against a 2,700+-chunk index. (Highly Engineered)
- Fused **Reciprocal Rank Fusion** at k=60 (Cormack et al.) across vector and BM25 retrievers, each fetching 2× the requested top-k to prevent rank collapse after fusion. (Highly Engineered)
"""


def _read_multiline(prompt: str) -> str:
    print(prompt)
    print("(type END on its own line when done)")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _read_topics() -> list[str]:
    print("\nEnter topic names (one per line, then END):")
    topics = []
    while True:
        line = input().strip()
        if line == "END":
            break
        if line:
            topics.append(line)
    return topics


def _generate(project: str, dense_paragraph: str, topics: list[str]) -> str:
    client = get_client()

    topic_list = "\n".join(f"- {t}" for t in topics)
    user_msg = f"""Project / Experience: {project}

Topics to generate bullets for:
{topic_list}

Dense paragraph (source material):
{dense_paragraph}

Generate exactly 8 bullets per topic (2 per voice style, in order: Results-Oriented, Architectural Focus, Concise & Punchy, Highly Engineered). Include the #### Topic: header for each topic."""

    print("\n[generator] Calling Claude...", flush=True)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


def _check_lengths(output: str) -> None:
    """Warn on any bullet exceeding 200 chars (bold markers excluded)."""
    import re
    over = []
    for i, line in enumerate(output.splitlines(), 1):
        if not line.startswith("- "):
            continue
        # strip voice suffix
        text = re.sub(r"\s*\([^)]+\)\s*$", "", line[2:])
        # strip bold markers for counting
        text_clean = text.replace("**", "")
        if len(text_clean) > 200:
            over.append((i, len(text_clean), line[:80]))
    if over:
        print(f"\n[generator] WARNING: {len(over)} bullet(s) exceed 200 chars:")
        for lineno, length, preview in over:
            print(f"  line {lineno} ({length} chars): {preview}...")


def main() -> None:
    print("=== Bullet Generator ===")
    print("Generates master.md-format bullets from a dense paragraph.")
    print("Output is a draft — review and edit before pasting into master.md.\n")

    project = input("Project / experience name (e.g. 'Mosaic Project'): ").strip()
    if not project:
        print("No project name given. Exiting.")
        return

    dense = _read_multiline("\nPaste the dense paragraph for this project:")
    if not dense.strip():
        print("No paragraph provided. Exiting.")
        return

    topics = _read_topics()
    if not topics:
        print("No topics provided. Exiting.")
        return

    output = _generate(project, dense, topics)

    _check_lengths(output)

    print("\n" + "─" * 60)
    print("GENERATED OUTPUT (paste into master.md after reviewing):")
    print("─" * 60)
    print(output)
    print("─" * 60)

    # Optionally save to a temp file
    out_path = _PROJECT_ROOT / ".tmp" / "generated_bullets.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"\nAlso saved to: {out_path}")


if __name__ == "__main__":
    main()
