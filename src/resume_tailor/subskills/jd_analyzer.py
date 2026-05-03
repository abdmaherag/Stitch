"""
JD Analyzer — Step 1 of the resume-tailor pipeline.

analyze(jd_text) -> dict
  Calls Claude with the JD Analyzer system prompt.
  Parses and validates the JSON response.
  Stores a sha256 of jd_text in scratch as `_jd_hash` so cached scratch can
  be safely matched to the JD on subsequent runs.
  Writes scratch/01-jd-analysis.json for debugging.
  Returns the parsed dict.
"""
import hashlib
import json
from pathlib import Path

from resume_tailor.client import get_client
from resume_tailor.prompts.jd_analyzer import SYSTEM_PROMPT


def jd_fingerprint(jd_text: str) -> str:
    """Stable fingerprint of JD text — whitespace-collapsed sha256."""
    import re
    normalized = re.sub(r"\s+", " ", jd_text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

SCRATCH_FILE = Path(__file__).parents[3] / "scratch" / "01-jd-analysis.json"
MODEL = "claude-sonnet-4-5"

REQUIRED_KEYS = {
    "role_purpose",
    "anchor_metadata",
    "frequency_score",
    "implied_skills",
    "narrative_strategy",
    "gap_mapping",
    "operational_context",
    "mirror_verbs",
}


def analyze(jd_text: str) -> dict:
    client = get_client()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": jd_text}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if the model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JD Analyzer returned invalid JSON: {e}\n\nRaw output:\n{raw}")

    missing = REQUIRED_KEYS - result.keys()
    if missing:
        raise ValueError(f"JD Analyzer response missing keys: {missing}")

    # Stamp the source JD's fingerprint so cache loads can verify on later runs
    result["_jd_hash"] = jd_fingerprint(jd_text)

    SCRATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCRATCH_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[jd_analyzer] scratch -> {SCRATCH_FILE}")

    return result
