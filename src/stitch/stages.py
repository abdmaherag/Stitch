"""Per-stage helpers that wrap the analyzer / writer / reviewer prompts.

Each function:
  1. Builds the user message from input file paths
  2. Calls the LLM via anthropic_client
  3. Writes the structured output to the per-company .tmp/<slug>/ directory
  4. Returns the parsed JSON (or raw text for JD raw)
"""

from __future__ import annotations

import json
from pathlib import Path

from anthropic import Anthropic

from .anthropic_client import (
    MODEL_OPUS,
    MODEL_SONNET,
    Stage,
    call_json,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / ".claude" / "skills" / "stitch" / "prompts"
MASTER_MD = PROJECT_ROOT / "master.md"
TEMPLATE_CONFIG = PROJECT_ROOT / "template-config.yaml"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_analyzer(client: Anthropic, tmp_dir: Path) -> dict:
    """Stage 1 — read .tmp/<slug>/jd-raw.txt, write jd-analysis.json."""
    jd_text = (tmp_dir / "jd-raw.txt").read_text(encoding="utf-8")
    stage = Stage(
        name="analyzer",
        model=MODEL_SONNET,
        system_prompt=_load_prompt("analyzer"),
        max_tokens=2000,
    )
    user_msg = f"<job_description>\n{jd_text}\n</job_description>"
    result = call_json(client, stage, user_msg)
    out_path = tmp_dir / "jd-analysis.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_writer(
    client: Anthropic,
    tmp_dir: Path,
    pass_index: int,
    previous_bullets: dict | None = None,
    review: dict | None = None,
) -> dict:
    """Stage 2 (or revision in Stage 4) — write bullets-v{pass_index}.json."""
    master_text = MASTER_MD.read_text(encoding="utf-8")
    config_text = TEMPLATE_CONFIG.read_text(encoding="utf-8")
    analysis = json.loads((tmp_dir / "jd-analysis.json").read_text(encoding="utf-8"))

    sections = [
        "<master_md>", master_text, "</master_md>",
        "<template_config_yaml>", config_text, "</template_config_yaml>",
        "<jd_analysis_json>", json.dumps(analysis, indent=2), "</jd_analysis_json>",
    ]

    if previous_bullets is not None and review is not None:
        sections.extend([
            "<previous_bullets_json>",
            json.dumps(previous_bullets, indent=2),
            "</previous_bullets_json>",
            "<review_json>",
            json.dumps(review, indent=2),
            "</review_json>",
            "<revision_instruction>",
            "This is a revision pass. Address every issue with severity 'critical' "
            "in the review. Leave non-critical bullets untouched unless context shifted.",
            "</revision_instruction>",
        ])

    user_msg = "\n".join(sections)
    stage = Stage(
        name=f"writer_pass{pass_index}",
        model=MODEL_OPUS,
        system_prompt=_load_prompt("writer"),
        max_tokens=4000,
    )
    result = call_json(client, stage, user_msg)
    out_path = tmp_dir / f"bullets-v{pass_index}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_reviewer(
    client: Anthropic,
    tmp_dir: Path,
    pass_index: int,
) -> dict:
    """Stage 3 (or 4b) — write review-v{pass_index}.json."""
    master_text = MASTER_MD.read_text(encoding="utf-8")
    config_text = TEMPLATE_CONFIG.read_text(encoding="utf-8")
    analysis = json.loads((tmp_dir / "jd-analysis.json").read_text(encoding="utf-8"))
    bullets = json.loads(
        (tmp_dir / f"bullets-v{pass_index}.json").read_text(encoding="utf-8")
    )

    user_msg = "\n".join([
        "<master_md>", master_text, "</master_md>",
        "<template_config_yaml>", config_text, "</template_config_yaml>",
        "<jd_analysis_json>", json.dumps(analysis, indent=2), "</jd_analysis_json>",
        "<bullets_json>", json.dumps(bullets, indent=2), "</bullets_json>",
    ])
    stage = Stage(
        name=f"reviewer_pass{pass_index}",
        model=MODEL_SONNET,
        system_prompt=_load_prompt("reviewer"),
        max_tokens=3000,
    )
    result = call_json(client, stage, user_msg)
    out_path = tmp_dir / f"review-v{pass_index}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def has_critical_issues(review: dict) -> bool:
    """True iff any bullet_issue has severity == 'critical'."""
    for issue in review.get("bullet_issues", []):
        if issue.get("severity") == "critical":
            return True
    return False
