"""
resume-tailor — interactive REPL entry point.

Usage:
    python -m resume_tailor.main
    # or, after pip install -e .:
    tailor

Paste the Job Description when prompted, then type END on its own line.
If scratch files from a previous run exist, you will be offered the option
to skip already-completed steps and resume from where the pipeline left off.
"""
import json
import re
from datetime import date
from pathlib import Path

from resume_tailor.subskills.master_parser   import parse    as parse_master
from resume_tailor.subskills.jd_analyzer     import analyze, jd_fingerprint
from resume_tailor.subskills.ranker          import rank
from resume_tailor.subskills.resume_selector import select
from resume_tailor.subskills.latex_editor    import edit
from resume_tailor.subskills.tracker_manager import append   as tracker_append

# Paths
_PKG_ROOT      = Path(__file__).parents[2]          # resume-tailor/
SCRATCH_DIR    = _PKG_ROOT / "scratch"
APPLICATIONS_DIR = _PKG_ROOT.parent / "applications"

SCRATCH_1  = SCRATCH_DIR / "01-jd-analysis.json"
SCRATCH_2A = SCRATCH_DIR / "02a-ranked-bullets.json"
SCRATCH_2B = SCRATCH_DIR / "02b-resume-selection.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_multiline(prompt: str) -> str:
    print(prompt)
    print("(paste content, then type END on its own line)")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _try_load(path: Path, label: str) -> dict | None:
    """
    If scratch file exists, ask user whether to load it and skip that step.
    Returns the loaded dict on yes, None on no or file absent.
    """
    if not path.exists():
        return None
    ans = input(f"  [{label}] scratch found — skip and load? [y/N]: ").strip().lower()
    if ans == "y":
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"    Loaded from {path.name}")
        return data
    return None


def _try_load_jd(path: Path, jd_text: str, label: str) -> dict | None:
    """
    Like _try_load but verifies the cached scratch was produced from the SAME JD.
    Compares jd_fingerprint(jd_text) to the cached `_jd_hash`. If different,
    refuses to load and forces a re-run — prevents silently using yesterday's
    JD analysis on today's job.
    """
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cached_hash = data.get("_jd_hash")
    current_hash = jd_fingerprint(jd_text)
    if cached_hash and cached_hash != current_hash:
        print(
            f"  [{label}] cached scratch is for a DIFFERENT JD "
            f"({cached_hash[:8]}... vs {current_hash[:8]}...) — re-running step 1."
        )
        return None
    if not cached_hash:
        print(f"  [{label}] cached scratch has no _jd_hash (older format) — cannot verify.")
    ans = input(f"  [{label}] scratch found and matches JD — skip and load? [y/N]: ").strip().lower()
    if ans == "y":
        print(f"    Loaded from {path.name}")
        return data
    return None


# ── Pipeline ──────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== resume-tailor ===")

    company  = input("\nCompany name: ").strip()
    role     = input("Role title:   ").strip()
    jd_link  = input("JD link (for tracker): ").strip()

    # Always paste JD first so cache loads can be hash-verified against it
    jd_text = _read_multiline("\nPaste the Job Description")

    print()
    cached_1  = _try_load_jd(SCRATCH_1, jd_text, "step 1  — JD analysis")

    # If step 1 re-ran (new JD), downstream scratch is stale — delete it silently
    # so the user can't accidentally load a selection from the wrong job.
    if cached_1 is None:
        for stale in (SCRATCH_2A, SCRATCH_2B):
            if stale.exists():
                stale.unlink()
                print(f"  [cache] deleted stale {stale.name} (new JD detected)")

    cached_2a = _try_load(SCRATCH_2A, "step 2A — ranked bullets")
    cached_2b = _try_load(SCRATCH_2B, "step 2B — resume selection")

    # ── Parse master.md (always fresh) ───────────────────────────────────────
    print("\n[0] Parsing master.md...")
    parsed = parse_master()
    print(
        f"    experience={list(parsed['experience'].keys())}  "
        f"projects={list(parsed['projects'].keys())}"
    )

    # ── Step 1 — JD Analyzer ─────────────────────────────────────────────────
    if cached_1 is not None:
        jd_analysis = cached_1
    else:
        print("\n[step 1] Analyzing Job Description...")
        jd_analysis = analyze(jd_text)
        print(json.dumps(jd_analysis, indent=2))

    # ── Step 2A — Ranker ─────────────────────────────────────────────────────
    if cached_2a is not None:
        ranked = cached_2a["ranked"]
    else:
        print("\n[step 2A] Ranking bullets...")
        ranked = rank(jd_analysis, parsed)
        for section, topics in ranked.items():
            for topic, data in topics.items():
                print(
                    f"    {section} / {topic}: "
                    f"{data['allocated_bullets']} bullet(s), "
                    f"{len(data['candidates'])} candidates"
                )

    # ── Step 2B — Resume Selector ─────────────────────────────────────────────
    if cached_2b is not None:
        selection = cached_2b
    else:
        print("\n[step 2B] Selecting and tailoring bullets...")
        selection = select(jd_analysis, ranked, parsed["skills_raw"])

    # ── Step 3 — LaTeX Editor ────────────────────────────────────────────────
    today       = date.today().strftime("%Y-%m-%d")
    folder_name = f"{today}-{_slugify(company)}"
    output_dir  = APPLICATIONS_DIR / folder_name

    print("\n[step 3] Filling LaTeX template...")
    resume_path = edit(selection, output_dir)
    print(f"  Resume -> {resume_path}")

    # ── Step 4 — Tracker ─────────────────────────────────────────────────────
    print("\n[step 4] Updating tracker...")
    tracker_append(
        company=company,
        role=role,
        jd_link=jd_link,
        folder_path=f"applications/{folder_name}/",
    )

    # ── Gap report ───────────────────────────────────────────────────────────
    gap_mappings = jd_analysis.get("gap_mapping", [])
    if gap_mappings:
        all_bullet_text = " ".join(
            (b["text"] if isinstance(b, dict) else b).lower().replace("**", "")
            for section in selection.get("bullets", {}).values()
            for b in section
        )
        print(f"\n{'─' * 50}")
        print("Gap report (JD pain points vs. selected bullets):")
        for gm in gap_mappings:
            gap  = gm.get("gap", "")
            slug = gm.get("target_topic_slug", "")
            sig_words = [w for w in gap.lower().split() if len(w) > 4]
            covered = any(w in all_bullet_text for w in sig_words)
            mark = "✓" if covered else "✗"
            print(f"  {mark} [{slug}] {gap}")

    # ── Operational context ──────────────────────────────────────────────────
    op_ctx = jd_analysis.get("operational_context", {})
    if op_ctx.get("work_environment") or op_ctx.get("stakeholders"):
        print(f"\n{'─' * 50}")
        print("Operational context (review before applying):")
        if op_ctx.get("work_environment"):
            print(f"  Work environment : {op_ctx['work_environment']}")
        if op_ctx.get("stakeholders"):
            print(f"  Stakeholders     : {op_ctx['stakeholders']}")

    # ── Final report ─────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"Done.  Resume -> {resume_path}")
    if selection.get("flags"):
        print("\nFlags to review:")
        for f in selection["flags"]:
            print(f"  ! {f}")


if __name__ == "__main__":
    main()
