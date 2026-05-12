"""Atom-grounding eval: verify every concrete claim in a generated bullet
appears verbatim in master.md.

An "atom" is a token that, if invented, would be a fabrication: numbers,
proper nouns / CamelCase identifiers, ALL_CAPS constants, version strings,
hyphenated tech names. We extract atoms from each bullet, then check each
atom appears verbatim somewhere in master.md (case-insensitive substring).

Score = grounded_atoms / total_atoms across the run. Target >= 0.95.

Usage:
    python -m eval.atom_grounding <path/to/bullets.json> <path/to/master.md>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Numbers: 100, 100GB, 1,000, 0.65, 384-dim, 2,781-chunk
NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?(?:[A-Za-z+%/]+)?\b")

# Tech tokens: CamelCase (FastAPI), ALL_CAPS_WITH_UNDERSCORES (NO_ANSWER_THRESHOLD),
# hyphenated tech (rank-bm25, llama-3.3-70b), dotted tech (sse-starlette).
TECH_RE = re.compile(
    r"\b("
    r"[A-Z][a-z]+(?:[A-Z][a-z0-9]*)+"          # FastAPI, ChromaDB
    r"|[A-Z]{2,}(?:[_-][A-Z0-9]{2,})+"         # NO_ANSWER_THRESHOLD
    r"|[A-Za-z]+(?:[-][A-Za-z0-9]+)+"          # rank-bm25, llama-3.3-70b
    r"|[A-Z][a-z]+\d+(?:[\.\-]\d+)*"           # Qwen3, llama2
    r")\b"
)

# Stop-list: common words that match TECH_RE but aren't real atoms
STOP_ATOMS = {
    "Built", "Designed", "Engineered", "Implemented", "Architected",
    "Configured", "Cut", "Reduced", "Improved", "Scaled", "Owned", "Led",
    "Wrote", "Diagnosed", "Drove", "Shipped", "Solved", "Streamlined",
    "Deployed", "Delivered", "Established", "Launched", "Refactored",
}


def extract_atoms(text: str) -> set[str]:
    """Extract concrete atoms from a bullet."""
    atoms = set()
    atoms.update(NUMBER_RE.findall(text))
    for match in TECH_RE.findall(text):
        if match not in STOP_ATOMS:
            atoms.add(match)
    return atoms


def is_grounded(atom: str, master_text: str) -> bool:
    """True if atom appears verbatim (case-insensitive) in master.md."""
    return atom.lower() in master_text.lower()


def evaluate(bullets_path: Path, master_path: Path) -> dict:
    bullets = json.loads(bullets_path.read_text(encoding="utf-8"))
    master_text = master_path.read_text(encoding="utf-8")

    total_atoms = 0
    grounded_atoms = 0
    failures: list[dict] = []

    def audit_slot(slot_id: str, slot_bullets: list[str]) -> None:
        nonlocal total_atoms, grounded_atoms
        for i, bullet in enumerate(slot_bullets):
            atoms = extract_atoms(bullet)
            for atom in atoms:
                total_atoms += 1
                if is_grounded(atom, master_text):
                    grounded_atoms += 1
                else:
                    failures.append({
                        "slot": slot_id,
                        "bullet_index": i,
                        "atom": atom,
                        "bullet": bullet,
                    })

    for role in bullets.get("roles", []):
        audit_slot(role["role_id"], role.get("bullets", []))
    for proj in bullets.get("projects", []):
        audit_slot(proj["project_id"], proj.get("bullets", []))

    score = grounded_atoms / total_atoms if total_atoms else 1.0
    return {
        "total_atoms": total_atoms,
        "grounded_atoms": grounded_atoms,
        "ungrounded_atoms": total_atoms - grounded_atoms,
        "score": round(score, 4),
        "passed": score >= 0.95,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bullets", type=Path, help="Path to bullets JSON")
    parser.add_argument("master", type=Path, help="Path to master.md")
    args = parser.parse_args()

    if not args.bullets.exists():
        sys.stderr.write(f"ERROR: {args.bullets} not found\n")
        return 1
    if not args.master.exists():
        sys.stderr.write(f"ERROR: {args.master} not found\n")
        return 1

    result = evaluate(args.bullets, args.master)

    print(f"Atom-grounding eval — {args.bullets.name}")
    print(f"  Total atoms:      {result['total_atoms']}")
    print(f"  Grounded:         {result['grounded_atoms']}")
    print(f"  Ungrounded:       {result['ungrounded_atoms']}")
    print(f"  Score:            {result['score']:.2%}")
    print(f"  Passed (>=95%):   {result['passed']}")

    if result["failures"]:
        print(f"\n  Ungrounded atoms ({len(result['failures'])}):")
        for f in result["failures"][:20]:  # cap for readability
            print(f"    [{f['slot']} #{f['bullet_index']}] {f['atom']!r}  in: {f['bullet'][:80]!r}")
        if len(result["failures"]) > 20:
            print(f"    ... and {len(result['failures']) - 20} more")

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
