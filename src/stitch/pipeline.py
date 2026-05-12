"""6-stage orchestrator. Standalone equivalent of SKILL.md.

Stage 0 → Resolve company + JD, slugify, save jd-raw.txt
Stage 1 → Analyzer subagent (Sonnet) writes jd-analysis.json
Stage 2 → Writer subagent (Opus) writes bullets-v1.json
Stage 3 → Reviewer subagent (Sonnet) writes review-v1.json
Stage 4 → Conditional revision (one extra writer + reviewer pass)
Stage 5 → Approval gate (CLI prompt)
Stage 6 → Render via scripts/fill_and_render.py (subprocess)
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .anthropic_client import make_client
from .slugify import slugify
from .stages import (
    PROJECT_ROOT,
    has_critical_issues,
    run_analyzer,
    run_reviewer,
    run_writer,
)


TMP_ROOT = PROJECT_ROOT / ".tmp"
OUT_ROOT = PROJECT_ROOT / "out"
RENDER_SCRIPT = PROJECT_ROOT / "scripts" / "fill_and_render.py"


def run_pipeline(
    company_name: str,
    jd_text: str,
    *,
    interactive_approval: bool = True,
) -> Path:
    """End-to-end run. Returns the path to the generated resume.pdf."""
    slug = slugify(company_name)
    tmp_dir = TMP_ROOT / slug
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "jd-raw.txt").write_text(jd_text, encoding="utf-8")
    print(f"[Stage 0] slug={slug!r}  tmp={tmp_dir.relative_to(PROJECT_ROOT)}")

    client = make_client()  # OAuth (preferred) or API key, see anthropic_client.make_client

    print("[Stage 1] Analyzer (Sonnet)...")
    analysis = run_analyzer(client, tmp_dir)
    print(
        f"          → company={analysis.get('company')!r}  "
        f"role={analysis.get('role_title')!r}  "
        f"required={len(analysis.get('required_skills', []))}  "
        f"keywords={len(analysis.get('keywords_to_emphasize', []))}"
    )

    print("[Stage 2] Writer pass 1 (Opus)...")
    bullets_v1 = run_writer(client, tmp_dir, pass_index=1)
    print(
        f"          → roles={len(bullets_v1.get('roles', []))}  "
        f"projects={len(bullets_v1.get('projects', []))}  "
        f"skills={sum(len(v) for v in bullets_v1.get('skills', {}).values())}"
    )

    print("[Stage 3] Reviewer pass 1 (Sonnet)...")
    review_v1 = run_reviewer(client, tmp_dir, pass_index=1)
    print(
        f"          → verdict={review_v1.get('verdict')!r}  "
        f"issues={len(review_v1.get('bullet_issues', []))}"
    )

    if has_critical_issues(review_v1):
        print("[Stage 4] Critical issues found. Writer pass 2 (Opus)...")
        bullets_v2 = run_writer(
            client, tmp_dir, pass_index=2,
            previous_bullets=bullets_v1,
            review=review_v1,
        )
        print(f"          → revised {len(bullets_v2.get('roles', [])) + len(bullets_v2.get('projects', []))} slots")

        print("[Stage 4] Reviewer pass 2 (informational)...")
        review_v2 = run_reviewer(client, tmp_dir, pass_index=2)
        print(f"          → verdict={review_v2.get('verdict')!r}")

        bullets_final = bullets_v2
        review_final = review_v2
        bullets_final_path = tmp_dir / "bullets-v2.json"
    else:
        print("[Stage 4] No critical issues. Skipping revision.")
        bullets_final = bullets_v1
        review_final = review_v1
        bullets_final_path = tmp_dir / "bullets-v1.json"

    print()
    print("=" * 70)
    print("[Stage 5] Approval gate")
    print("=" * 70)
    _print_for_approval(bullets_final, review_final)

    if interactive_approval:
        if not _prompt_approval():
            print("Aborted by user. No render performed.")
            return tmp_dir / "ABORTED"

    today = dt.date.today().isoformat()
    out_dir = OUT_ROOT / f"{slug}-{today}"
    print(f"\n[Stage 6] Rendering to {out_dir.relative_to(PROJECT_ROOT)} ...")

    cmd = [
        sys.executable,
        str(RENDER_SCRIPT),
        "--bullets", str(bullets_final_path),
        "--jd", str(tmp_dir / "jd-raw.txt"),
        "--out", str(out_dir),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    print(completed.stdout)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        raise RuntimeError(
            f"fill_and_render.py exited {completed.returncode}. See stderr above."
        )

    pdf_path = out_dir / "resume.pdf"
    print(f"\nDone. PDF: {pdf_path}")
    return pdf_path


def _print_for_approval(bullets: dict, review: dict) -> None:
    print("\n## Tailored bullets\n")
    for role in bullets.get("roles", []):
        print(f"### {role['role_id']} ({len(role['bullets'])} bullets)")
        for i, b in enumerate(role["bullets"], 1):
            print(f"  {i}. {b}")
        print()
    for proj in bullets.get("projects", []):
        print(f"### {proj['project_id']} ({len(proj['bullets'])} bullets)")
        for i, b in enumerate(proj["bullets"], 1):
            print(f"  {i}. {b}")
        print()

    skills = bullets.get("skills", {})
    print("## Skills")
    for cat in ("Languages", "AI&ML", "Concepts & Tools"):
        items = skills.get(cat, [])
        print(f"- {cat}: {', '.join(items)}")
    print()

    issues = review.get("bullet_issues", [])
    if issues:
        print("## Reviewer notes")
        for issue in issues:
            sev = issue.get("severity", "?")
            cat = issue.get("category", "?")
            problem = issue.get("problem", "")
            print(f"- [{sev}/{cat}] {problem}")
        print()


def _prompt_approval() -> bool:
    while True:
        ans = input("Approve to render PDF? [yes/no]: ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please answer 'yes' or 'no'.")
