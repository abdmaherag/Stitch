"""CLI entry point: `python -m resume_test ...`"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resume-test",
        description="Tailor a resume to a job description via 3-agent pipeline.",
    )
    parser.add_argument(
        "--company", required=True,
        help="Target company name (will be slugified for folder names)."
    )
    parser.add_argument(
        "--jd", required=True,
        help="Path to a JD text file, or '-' to read JD from stdin."
    )
    parser.add_argument(
        "--no-approval", action="store_true",
        help="Skip the interactive approval gate. Render immediately after reviewer."
    )
    args = parser.parse_args(argv)

    if args.jd == "-":
        jd_text = sys.stdin.read()
    else:
        jd_path = Path(args.jd)
        if not jd_path.exists():
            sys.stderr.write(f"ERROR: JD file not found: {jd_path}\n")
            return 1
        jd_text = jd_path.read_text(encoding="utf-8")

    if not jd_text.strip():
        sys.stderr.write("ERROR: JD text is empty.\n")
        return 1

    try:
        run_pipeline(
            company_name=args.company,
            jd_text=jd_text,
            interactive_approval=not args.no_approval,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        return 130
    except Exception as e:
        sys.stderr.write(f"Pipeline failed: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
