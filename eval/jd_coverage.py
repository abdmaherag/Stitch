"""JD coverage eval: what fraction of the JD's required/preferred skills and
keywords appear in the rendered resume text?

Reads the analyzer's jd-analysis.json + the writer's bullets.json. Checks
each required_skills / preferred_skills / keywords_to_emphasize entry as
a case-insensitive substring of the joined bullet + skills text.

Two scores:
    required_coverage  = found_required / total_required   (target >= 0.80)
    keyword_coverage   = found_keywords / total_keywords   (target >= 0.50)

Usage:
    python -m eval.jd_coverage <bullets.json> <jd-analysis.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def collect_resume_text(bullets: dict) -> str:
    """Concatenate every bullet + every skill into a single searchable blob."""
    parts: list[str] = []
    for role in bullets.get("roles", []):
        parts.extend(role.get("bullets", []))
    for proj in bullets.get("projects", []):
        parts.extend(proj.get("bullets", []))
    skills = bullets.get("skills", {})
    for category_items in skills.values():
        parts.extend(category_items)
    return "\n".join(parts)


def coverage(items: list[str], resume_text: str) -> tuple[list[str], list[str]]:
    """Returns (found, missing). Substring match, case-insensitive."""
    text_lower = resume_text.lower()
    found, missing = [], []
    for item in items:
        if item.lower() in text_lower:
            found.append(item)
        else:
            missing.append(item)
    return found, missing


def evaluate(bullets_path: Path, analysis_path: Path) -> dict:
    bullets = json.loads(bullets_path.read_text(encoding="utf-8"))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

    resume_text = collect_resume_text(bullets)

    required = analysis.get("required_skills", [])
    preferred = analysis.get("preferred_skills", [])
    keywords = analysis.get("keywords_to_emphasize", [])

    req_found, req_missing = coverage(required, resume_text)
    pref_found, pref_missing = coverage(preferred, resume_text)
    kw_found, kw_missing = coverage(keywords, resume_text)

    return {
        "required": {
            "total": len(required),
            "found": len(req_found),
            "missing": req_missing,
            "score": (len(req_found) / len(required)) if required else 1.0,
        },
        "preferred": {
            "total": len(preferred),
            "found": len(pref_found),
            "missing": pref_missing,
            "score": (len(pref_found) / len(preferred)) if preferred else 1.0,
        },
        "keywords": {
            "total": len(keywords),
            "found": len(kw_found),
            "missing": kw_missing,
            "score": (len(kw_found) / len(keywords)) if keywords else 1.0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bullets", type=Path)
    parser.add_argument("analysis", type=Path)
    args = parser.parse_args()

    if not args.bullets.exists():
        sys.stderr.write(f"ERROR: {args.bullets} not found\n")
        return 1
    if not args.analysis.exists():
        sys.stderr.write(f"ERROR: {args.analysis} not found\n")
        return 1

    result = evaluate(args.bullets, args.analysis)

    print(f"JD coverage eval — {args.bullets.name}")
    for tier in ("required", "preferred", "keywords"):
        r = result[tier]
        print(f"  {tier:10s}  {r['found']}/{r['total']}  ({r['score']:.0%})")
        if r["missing"]:
            preview = ", ".join(r["missing"][:8])
            more = f" (+{len(r['missing']) - 8} more)" if len(r["missing"]) > 8 else ""
            print(f"             missing: {preview}{more}")

    required_pass = result["required"]["score"] >= 0.80
    keyword_pass = result["keywords"]["score"] >= 0.50
    print()
    print(f"  Required >= 80%: {'PASS' if required_pass else 'FAIL'}")
    print(f"  Keywords >= 50%: {'PASS' if keyword_pass else 'FAIL'}")

    return 0 if (required_pass and keyword_pass) else 2


if __name__ == "__main__":
    sys.exit(main())
