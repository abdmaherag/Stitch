"""
Master Parser — parses master.md into a structured dict at runtime.
master.md remains the single source of truth; this runs on every pipeline call.

Bullet IDs are HASH-BASED (sha1 of normalized text, first 6 hex chars).
Reordering bullets in master.md does NOT shift IDs — cached scratch files
remain valid as long as bullet text is unchanged.

Returns:
{
  "experience": {
    "exp": {
      "Email RAG System": [
        {"id": "exp.email_rag.a3f1c2", "text": "...", "voice": "Results-Oriented"},
        ...
      ],
      ...
    }
  },
  "projects": {
    "mosaic": { "RAG / Retrieval": [...], ... },
    "weather": { "ML / Modeling": [...], ... }
  },
  "skills_raw": "full text of the ## Skills section"
}
"""
import hashlib
import re
from pathlib import Path

MASTER_MD = Path(__file__).parents[3] / "master.md"

VOICE_LABELS = {
    "Results-Oriented",
    "Architectural Focus",
    "Concise & Punchy",
    "Highly Engineered",
}

# Display name → short slug used in bullet IDs
TOPIC_SLUGS: dict[str, str] = {
    "Email RAG System":            "email_rag",
    "AI Chatbot":                  "ai_chatbot",
    "Full-Stack Web":              "fullstack",
    "RAG / Retrieval":             "rag",
    "AI / ML Engineering":         "ai_ml",
    "Backend":                     "backend",
    "Eval / Testing":              "eval",
    "ML / Modeling":               "ml",
    "Data Engineering / Pipelines":"data_eng",
    "Eval / Testing / Statistics": "eval_stats",
    "Research / Methodology":      "research",
}

# Substring to match in ### headers → (section_key, project_slug)
PROJECT_MAP: list[tuple[str, str, str]] = [
    ("AI Engineer",            "experience", "exp"),
    ("Mosaic Project",         "projects",   "mosaic"),
    ("Weather Forecast Project","projects",  "weather"),
]


def _extract_voice(text: str) -> tuple[str, str]:
    for label in VOICE_LABELS:
        suffix = f"({label})"
        if text.endswith(suffix):
            return text[: -len(suffix)].rstrip(". "), label
    return text, "Unknown"


def _bullet_id(proj_slug: str, topic_slug: str, text: str) -> str:
    """Stable hash-based ID. Whitespace-normalized so trivial edits don't shift IDs."""
    normalized = re.sub(r"\s+", " ", text.strip())
    h = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:6]
    return f"{proj_slug}.{topic_slug}.{h}"


def parse(path: Path | None = None) -> dict:
    md = (path or MASTER_MD).read_text(encoding="utf-8")
    lines = md.splitlines()

    result: dict = {"experience": {}, "projects": {}, "skills_raw": ""}

    cur_section: str | None  = None   # "experience" | "projects" | "skills"
    cur_proj_section: str | None = None  # "experience" | "projects"
    cur_proj_slug: str | None    = None  # "exp" | "mosaic" | "weather"
    cur_topic: str | None        = None
    seen_ids: set[str]           = set()
    skills_lines: list[str]      = []
    in_skills = False

    for line in lines:
        # ── top-level section headers ──────────────────────────────────────
        if line.startswith("## Experience"):
            cur_section = "experience"; in_skills = False; continue
        if line.startswith("## Projects"):
            cur_section = "projects";  in_skills = False; continue
        if line.startswith("## Skills"):
            cur_section = "skills";    in_skills = True;  continue

        if in_skills:
            skills_lines.append(line)
            continue

        if cur_section is None:
            continue

        # ── project / subsection  (### …) ─────────────────────────────────
        if line.startswith("### "):
            header = line[4:].strip()
            cur_proj_section = None
            cur_proj_slug    = None
            cur_topic        = None
            for match_str, sec, slug in PROJECT_MAP:
                if match_str in header:
                    cur_proj_section = sec
                    cur_proj_slug    = slug
                    if slug not in result[sec]:
                        result[sec][slug] = {}
                    break
            continue

        # ── topic header  (#### Topic: …) ─────────────────────────────────
        if line.startswith("#### Topic: "):
            cur_topic = line[12:].strip()
            if cur_proj_slug and cur_proj_section:
                result[cur_proj_section][cur_proj_slug].setdefault(cur_topic, [])
            continue

        # ── bullet  (- …) ─────────────────────────────────────────────────
        if (
            line.startswith("- ")
            and cur_topic
            and cur_proj_slug
            and cur_proj_section
        ):
            text = line[2:].strip()
            clean, voice = _extract_voice(text)
            if voice == "Unknown":
                print(f"[master_parser] WARNING: unrecognized voice label — {text[:80]!r}")

            slug = TOPIC_SLUGS.get(cur_topic, cur_topic.lower().replace(" ", "_")[:12])
            bid  = _bullet_id(cur_proj_slug, slug, clean)
            if bid in seen_ids:
                # Two bullets normalize to identical text — flag and skip the duplicate
                print(f"[master_parser] WARNING: duplicate bullet id {bid} — {clean[:80]!r}")
                continue
            seen_ids.add(bid)

            result[cur_proj_section][cur_proj_slug][cur_topic].append({
                "id":    bid,
                "text":  clean,
                "voice": voice,
            })

    result["skills_raw"] = "\n".join(skills_lines).strip()
    return result
