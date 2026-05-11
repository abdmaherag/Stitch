"""Fill template.docx with bullets/skills JSON, render to PDF via Word."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml
from docx2pdf import convert
from docxtpl import DocxTemplate


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DOCX = PROJECT_ROOT / "template.docx"
TEMPLATE_CONFIG = PROJECT_ROOT / "template-config.yaml"


def build_context(bullets: dict, config: dict) -> dict:
    """Flatten bullets JSON into Jinja context keys the .docx expects.

    Per-role/project bullets are exposed as `<id>_bullets` (a list). Skills are
    exposed as `skills_languages`, `skills_aiml`, `skills_concepts_tools`
    (joined strings, since skills sit on a single line per category).
    """
    context: dict = {}

    config_role_ids = {r["id"] for r in config.get("roles", [])}
    config_project_ids = {p["id"] for p in config.get("projects", [])}

    for role in bullets.get("roles", []):
        rid = role["role_id"]
        if rid not in config_role_ids:
            sys.exit(f"ERROR: role_id '{rid}' in bullets.json not found in template-config.yaml")
        context[f"{rid}_bullets"] = role["bullets"]

    for proj in bullets.get("projects", []):
        pid = proj["project_id"]
        if pid not in config_project_ids:
            sys.exit(f"ERROR: project_id '{pid}' in bullets.json not found in template-config.yaml")
        context[f"{pid}_bullets"] = proj["bullets"]

    skills = bullets.get("skills", {})
    context["skills_languages"] = ", ".join(skills.get("Languages", []))
    context["skills_aiml"] = ", ".join(skills.get("AI&ML", []))
    context["skills_concepts_tools"] = ", ".join(skills.get("Concepts & Tools", []))

    return context


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill template.docx and render PDF.")
    parser.add_argument("--bullets", required=True, help="Path to bullets JSON file")
    parser.add_argument("--out", required=True, help="Output folder (will be created)")
    parser.add_argument("--jd", help="Optional JD text file to copy into output folder")
    args = parser.parse_args()

    bullets_path = Path(args.bullets)
    out_dir = Path(args.out)

    if not TEMPLATE_DOCX.exists():
        sys.exit(f"ERROR: template not found at {TEMPLATE_DOCX}. Run /resume-test --setup.")
    if not TEMPLATE_CONFIG.exists():
        sys.exit(f"ERROR: config not found at {TEMPLATE_CONFIG}. Run /resume-test --setup.")
    if not bullets_path.exists():
        sys.exit(f"ERROR: bullets file not found at {bullets_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    bullets = json.loads(bullets_path.read_text(encoding="utf-8"))
    config = yaml.safe_load(TEMPLATE_CONFIG.read_text(encoding="utf-8"))
    context = build_context(bullets, config)

    docx_out = out_dir / "resume.docx"
    pdf_out = out_dir / "resume.pdf"

    doc = DocxTemplate(str(TEMPLATE_DOCX))
    doc.render(context)
    doc.save(str(docx_out))
    print(f"Wrote {docx_out}")

    convert(str(docx_out), str(pdf_out))
    print(f"Wrote {pdf_out}")

    shutil.copy(bullets_path, out_dir / "bullets.json")
    if args.jd:
        jd_path = Path(args.jd)
        if jd_path.exists():
            shutil.copy(jd_path, out_dir / "jd.txt")

    print(f"\nOutput folder: {out_dir}")
    for f in sorted(out_dir.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
