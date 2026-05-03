"""
Tracker Manager — Step 4 of the resume-tailor pipeline.

append(company, role, jd_link, folder_path) -> None
  Pure Python — no Claude call.
  Appends one row to applications/0tracker.csv.
  Creates the file with a header row on first run.
"""
from datetime import date
from pathlib import Path

TRACKER = Path(__file__).parents[4] / "applications" / "0tracker.csv"
HEADER = "date,company,role,jd_link,folder_path,status\n"


def append(
    company: str,
    role: str,
    jd_link: str,
    folder_path: str,
    status: str = "Applied",
) -> None:
    if not TRACKER.parent.exists():
        TRACKER.parent.mkdir(parents=True, exist_ok=True)

    write_header = not TRACKER.exists() or TRACKER.stat().st_size == 0
    today = date.today().strftime("%Y-%m-%d")

    # Wrap fields that may contain commas in double-quotes
    def _q(val: str) -> str:
        return f'"{val}"' if "," in val else val

    row = f"{today},{_q(company)},{_q(role)},{_q(jd_link)},{_q(folder_path)},{status}\n"

    with TRACKER.open("a", encoding="utf-8") as f:
        if write_header:
            f.write(HEADER)
        f.write(row)

    print(f"[tracker] appended -> {TRACKER}")
