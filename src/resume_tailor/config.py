"""
Loads stitch.yaml — the personal pipeline config that drives all hardcoded section
references (master_parser, ranker, resume_selector, latex_editor).

Copy stitch.example.yaml → stitch.yaml and fill in your own sections.
"""
import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).parents[2] / "stitch.yaml"


def load() -> dict:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"stitch.yaml not found at {_CONFIG_PATH}\n"
            "Copy stitch.example.yaml → stitch.yaml and fill in your sections."
        )
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


def get_sections() -> list[dict]:
    return load()["sections"]


def get_project_map() -> list[tuple[str, str, str]]:
    """[(master_label_substr, master_section, master_slug), ...]
    Used by master_parser to map ### headers → structured dict keys."""
    return [(s["master_label"], s["master_section"], s["master_slug"])
            for s in get_sections()]


def get_ranker_sections() -> dict:
    """{key: {parsed_path, budget, max_topics, min_score_pct}}
    Used by ranker to know which sections to score and how to allocate budget."""
    out = {}
    for s in get_sections():
        out[s["key"]] = {
            "parsed_path":   (s["master_section"], s["master_slug"]),
            "budget":         s["budget"],
            "max_topics":     s.get("max_topics", 2),
            "min_score_pct":  s.get("min_score_pct", 0.65),
        }
    return out


def get_bullet_budgets() -> dict:
    """{key: budget} — used by resume_selector to validate bullet counts."""
    return {s["key"]: s["budget"] for s in get_sections()}
