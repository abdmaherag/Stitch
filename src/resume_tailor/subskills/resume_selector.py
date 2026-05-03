"""
Resume Selector — Step 2B of the resume-tailor pipeline.

select(jd_analysis, ranked_candidates, skills_raw) -> dict
  Calls Claude with the pre-ranked candidates from 2A.
  Claude picks final bullets, applies light edits, filters skills, writes summary.
  Validates schema, char limits, self_review flags, and picked IDs.
  Retries once on validation failure before raising.
  Writes scratch/02b-resume-selection.json.
  Returns the parsed dict.

Bullet schema (B1/B2): each bullet is {"id": ..., "text": ...}.
  - id must come from THAT section's candidates (no cross-section borrowing)
  - text must pass FIVE content checks against the source candidate:
      * source coverage   >= _required_coverage(src_size)  (rewrite detector,
                                                            tighter for short bullets)
      * edit faithfulness >= MIN_EDIT_FAITHFULNESS         (fabrication detector)
      * sequence similarity >= MIN_SEQUENCE_SIM            (reorder detector)
      * numeric verbatim    (every number+unit in edit must appear in source)
      * no antonym swaps    (semantic direction preserved)
  - On validation failure, attempt 2 receives a follow-up message containing the
    exact errors — feedback retry, not blind retry.
"""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from resume_tailor.client import get_client
from resume_tailor.prompts.resume_selector import SYSTEM_PROMPT
from resume_tailor import config as _cfg

SCRATCH_FILE = Path(__file__).parents[3] / "scratch" / "02b-resume-selection.json"
MODEL = "claude-sonnet-4-5"

BULLET_BUDGETS  = _cfg.get_bullet_budgets()  # loaded from stitch.yaml
REQUIRED_KEYS   = {"bullets", "skills", "summary",
                   "selection_log", "self_review", "flags"}
REQUIRED_SKILLS = {"ai_ml", "concepts_tools"}

# Source coverage: how much of the SOURCE survived in the edit (rewrite detector).
# Length-scaled via _required_coverage(): tiny bullets get tighter thresholds because
# proportional drops are more destructive when there are only 5-6 content tokens.
MIN_SOURCE_COVERAGE = 0.7

# Edit faithfulness: how much of the EDIT comes from the source (fabrication detector).
MIN_EDIT_FAITHFULNESS = 0.65

# Sequence similarity: order-aware ratio between source and edit token streams.
# Catches reorderings that set-based overlap can't see — e.g. "Reduced X via Y" → "Reduced Y via X".
MIN_SEQUENCE_SIM = 0.55

# Stopwords excluded from overlap counting so "the/of/and/a" can't pad the score.
_STOPWORDS = {
    "the", "a", "an", "of", "and", "to", "in", "for", "with", "on", "by", "from",
    "is", "are", "be", "was", "were", "as", "at", "or", "but", "if", "this",
    "that", "it", "its", "their", "them", "we", "our", "you", "your", "have",
    "has", "had", "will", "would", "should", "could", "can", "may", "via",
    "into", "onto", "than", "then", "also", "such", "any", "all", "must",
    "need", "able", "using", "used", "use", "not", "no", "do", "does", "did",
}

# Antonym pairs — if source uses one form and edit replaces it with the other,
# the bullet's semantic direction has been inverted. Keys are stems; matching
# is form-aware (handles -ed / -ing / -s / -d).
_ANTONYM_PAIRS: list[tuple[str, str]] = [
    # Outcome / direction
    ("increase",     "reduce"),
    ("increase",     "decrease"),
    ("improve",      "degrade"),
    ("improve",      "worsen"),
    ("expand",       "shrink"),
    ("grow",         "cut"),
    ("accelerate",   "slow"),
    # Lifecycle
    ("add",          "remove"),
    ("add",          "drop"),
    ("build",        "destroy"),
    ("ship",         "abandon"),
    ("launch",       "retire"),
    ("achieve",      "miss"),
    ("achieve",      "fail"),
    # Capability
    ("enable",       "block"),
    ("enable",       "disable"),
    ("allow",        "forbid"),
    ("permit",       "deny"),
    # Domain-specific (AI / infra / arch)
    ("async",        "sync"),
    ("asynchronous", "synchronous"),
    ("streaming",    "batch"),
    ("parallel",     "sequential"),
    ("distributed",  "centralized"),
    ("dynamic",      "static"),
    ("online",       "offline"),
    ("cached",       "uncached"),
    ("compressed",   "uncompressed"),
    ("encrypted",    "unencrypted"),
    ("hybrid",       "vector"),  # hybrid retrieval vs vector-only is a real flip in this codebase
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_valid_ids_by_section(ranked_candidates: dict) -> dict[str, set[str]]:
    """Per-section candidate ID sets — used to forbid cross-section reuse (B2)."""
    out: dict[str, set[str]] = {}
    for section, section_data in ranked_candidates.items():
        ids: set[str] = set()
        for topic_data in section_data.values():
            for c in topic_data.get("candidates", []):
                ids.add(c["id"])
        out[section] = ids
    return out


def _build_id_lookup(ranked_candidates: dict) -> dict[str, dict]:
    """id -> {voice, text, section, topic} for downstream checks."""
    out: dict[str, dict] = {}
    for section, section_data in ranked_candidates.items():
        for topic, topic_data in section_data.items():
            for c in topic_data.get("candidates", []):
                out[c["id"]] = {
                    "voice":   c.get("voice", "Unknown"),
                    "text":    c.get("text", ""),
                    "section": section,
                    "topic":   topic,
                }
    return out


_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Numeric phrase = digits (with optional comma-thousands and decimals) + optional unit suffix.
# Captures: 132,777 / 2.21 / 40% / 60ms / 2.21°C / 390K / 50GB / 100x
# We over-capture suffixes here; _KNOWN_UNITS below filters out sentence words.
_NUM_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(%|°[a-z]|[a-z]{1,5}\b|[×x](?=\b|\s|$))?",
    re.IGNORECASE,
)

# Whitelist of recognized unit suffixes. Anything outside this set (e.g. "on", "by",
# "documents") is treated as a sentence word, not a unit, and dropped from the
# numeric phrase. False negatives (a missing real unit) just collapse to a bare
# number — the worst case is that a unit-only swap goes undetected. False positives
# (sentence word treated as unit) used to break number checks for any number not at
# end-of-sentence — much worse, so the whitelist is the safer side.
_KNOWN_UNITS = {
    "%",
    # Order-of-magnitude / SI prefixes
    "k", "m", "b", "t",
    # Storage
    "kb", "mb", "gb", "tb", "pb", "kib", "mib", "gib", "tib", "bps",
    # Time
    "ns", "us", "ms", "s", "sec", "secs", "min", "mins",
    "hr", "hrs", "h", "d", "mo", "yr", "yrs",
    # Length / area / volume
    "mm", "cm", "km",
    # Throughput / rate
    "fps", "rpm", "rps", "qps", "hz", "khz", "mhz", "ghz", "thz",
    "gbps", "mbps", "kbps",
    # Resolution / display
    "dpi", "ppi", "px",
    # Misc
    "x", "×",
}


def _normalize_unit(raw: str) -> str:
    """Returns lowercased unit if it's recognized, else empty string."""
    u = raw.lower().strip()
    if not u:
        return ""
    if u.startswith("°"):    # °c / °f always a unit
        return u
    if u in _KNOWN_UNITS:
        return u
    return ""


def _content_tokens(s: str) -> set[str]:
    """Lowercase alphanumeric tokens minus stopwords and bold markers."""
    raw = _TOKEN_RE.findall(s.lower().replace("**", ""))
    return {t for t in raw if t not in _STOPWORDS}


def _content_token_list(s: str) -> list[str]:
    """Order-preserving variant of _content_tokens — needed for sequence similarity."""
    raw = _TOKEN_RE.findall(s.lower().replace("**", ""))
    return [t for t in raw if t not in _STOPWORDS]


def _overlap_two_way(edited: str, source: str) -> tuple[float, float]:
    """Returns (source_coverage, edit_faithfulness).
      source_coverage: fraction of source content tokens preserved in edit
      edit_faithfulness: fraction of edit content tokens that came from source
    Both should be high. Empty input edge cases return 1.0 (degenerate)."""
    src  = _content_tokens(source)
    edit = _content_tokens(edited)
    if not src or not edit:
        return 1.0, 1.0
    inter = src & edit
    return len(inter) / len(src), len(inter) / len(edit)


def _sequence_similarity(edited: str, source: str) -> float:
    """Order-aware similarity between content-token streams (difflib ratio).
    1.0 = identical sequence, 0.0 = entirely shuffled. Set-overlap can be high
    while this is low — that's the reordering signature."""
    s_tokens = _content_token_list(source)
    e_tokens = _content_token_list(edited)
    if not s_tokens or not e_tokens:
        return 1.0
    return SequenceMatcher(None, s_tokens, e_tokens, autojunk=False).ratio()


def _required_coverage(src_size: int) -> float:
    """Tighter coverage thresholds for short bullets — 70% of 5 tokens means
    Claude can drop 1.5 tokens (basically anything), which is too permissive."""
    if src_size <= 5:
        return 0.85
    if src_size <= 10:
        return 0.80
    return MIN_SOURCE_COVERAGE


def _numbers_in(text: str) -> set[str]:
    """Extract numeric phrases (number + unit) as normalized strings.
    `60` and `60ms` are distinct. `40%` and `40` are distinct.
    Commas stripped from thousands so `132,777` and `132777` compare equal.
    Sentence words ("on", "by", "documents") are not treated as units."""
    out: set[str] = set()
    for num, unit in _NUM_RE.findall(text):
        n = num.replace(",", "")
        u = _normalize_unit(unit or "")
        out.add(f"{n}{u}" if u else n)
    return out


def _check_numbers(edited: str, source: str) -> str | None:
    """Every numeric phrase in edited must also appear in source. Source can have
    extras (trim is OK). `60` swapped to `60ms` is caught — different phrase."""
    invented = _numbers_in(edited) - _numbers_in(source)
    if invented:
        return f"invented numeric value(s): {sorted(invented)} (not in source)"
    return None


def _has_verb_form(text: str, base: str) -> bool:
    """True if text contains base, base+s, base+ed, base+ing, base+d (e-ending handled).
    Used by antonym detector — form-aware so 'increased' matches base 'increase'."""
    forms = {base, base + "s", base + "ed", base + "ing", base + "d"}
    if base.endswith("e"):
        forms.add(base[:-1] + "ing")  # increase -> increasing (not increaseing)
    text_tokens = set(_TOKEN_RE.findall(text.lower()))
    return bool(forms & text_tokens)


def _check_antonyms(edited: str, source: str) -> str | None:
    """Detect inverted-meaning swaps. If source uses A and edit uses B (the opposite)
    while the original A is gone, that's a semantic inversion."""
    for a, b in _ANTONYM_PAIRS:
        src_a, src_b = _has_verb_form(source, a), _has_verb_form(source, b)
        edit_a, edit_b = _has_verb_form(edited, a), _has_verb_form(edited, b)
        if src_a and edit_b and not edit_a and not src_b:
            return f"antonym swap: source uses {a!r}, edit uses {b!r}"
        if src_b and edit_a and not edit_b and not src_a:
            return f"antonym swap: source uses {b!r}, edit uses {a!r}"
    return None


def _check_voice_variety(result: dict, id_lookup: dict[str, dict]) -> list[str]:
    """Voice variety per section, read from bullet IDs (not from selection_log
    or self_review). Claude can't fake this."""
    errors: list[str] = []
    bullets = result.get("bullets", {})
    for section, section_bullets in bullets.items():
        voices: list[tuple[str, str]] = []
        for b in section_bullets:
            if not isinstance(b, dict):
                continue  # schema error already reported elsewhere
            bid = b.get("id", "")
            voice = id_lookup.get(bid, {}).get("voice", "Unknown")
            voices.append((bid, voice))
        voice_only = [v for _, v in voices]
        if len(voice_only) > 1 and len(set(voice_only)) < len(voice_only):
            errors.append(f"voice variety failed in {section}: {voices}")
    return errors


def _validate(result: dict, ranked_candidates: dict) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_KEYS - result.keys()
    if missing:
        errors.append(f"Missing top-level keys: {missing}")
        return errors  # can't go deeper safely

    valid_by_section = _build_valid_ids_by_section(ranked_candidates)
    id_lookup        = _build_id_lookup(ranked_candidates)

    bullets = result.get("bullets", {})

    # Per-section validation: count, schema, char limit, cross-section ID, overlap
    for section, budget in BULLET_BUDGETS.items():
        section_bullets = bullets.get(section, [])

        if len(section_bullets) != budget:
            errors.append(
                f"bullets.{section}: expected {budget}, got {len(section_bullets)}"
            )

        section_valid_ids = valid_by_section.get(section, set())

        for i, b in enumerate(section_bullets):
            # Schema: must be dict with id + text
            if not isinstance(b, dict) or "id" not in b or "text" not in b:
                errors.append(
                    f"bullets.{section}[{i}] must be an object with 'id' and 'text' "
                    f"(got: {type(b).__name__})"
                )
                continue

            bid  = b["id"]
            text = b["text"]

            # Char limit (bold markers excluded)
            plain = text.replace("**", "")
            if len(plain) > 200:
                errors.append(
                    f"bullets.{section}[{i}] exceeds 200 chars ({len(plain)}): {plain[:60]}..."
                )

            # B2: cross-section enforcement
            if bid not in section_valid_ids:
                # Diagnose: was it from a different section, or fabricated entirely?
                source = id_lookup.get(bid)
                if source:
                    errors.append(
                        f"bullets.{section}[{i}] uses id {bid!r} from section "
                        f"{source['section']!r} — cross-section reuse forbidden"
                    )
                else:
                    errors.append(
                        f"bullets.{section}[{i}] uses unknown id {bid!r} "
                        f"(not in any section's candidates)"
                    )
                continue  # can't overlap-check unknown id

            # B1 group: source coverage + edit faithfulness + sequence similarity
            #           + number verbatim + antonym check
            source_text = id_lookup[bid]["text"]
            src_cov, edit_faith = _overlap_two_way(text, source_text)
            seq_sim = _sequence_similarity(text, source_text)

            # Length-scaled coverage threshold — tighter for short bullets.
            src_size = len(_content_tokens(source_text))
            req_cov  = _required_coverage(src_size)

            if src_cov < req_cov:
                errors.append(
                    f"bullets.{section}[{i}] ({bid}) source coverage {src_cov:.0%} "
                    f"< {req_cov:.0%} (required for {src_size}-token source) — "
                    f"too much of the source was dropped. "
                    f"Source: {source_text[:80]!r} | Edited: {plain[:80]!r}"
                )
            if edit_faith < MIN_EDIT_FAITHFULNESS:
                errors.append(
                    f"bullets.{section}[{i}] ({bid}) edit faithfulness {edit_faith:.0%} "
                    f"< {MIN_EDIT_FAITHFULNESS:.0%} — edit contains too much novel content. "
                    f"Source: {source_text[:80]!r} | Edited: {plain[:80]!r}"
                )
            if seq_sim < MIN_SEQUENCE_SIM:
                errors.append(
                    f"bullets.{section}[{i}] ({bid}) sequence similarity {seq_sim:.0%} "
                    f"< {MIN_SEQUENCE_SIM:.0%} — clauses appear reordered. "
                    f"Source: {source_text[:80]!r} | Edited: {plain[:80]!r}"
                )

            num_err = _check_numbers(text, source_text)
            if num_err:
                errors.append(f"bullets.{section}[{i}] ({bid}) {num_err}")

            ant_err = _check_antonyms(text, source_text)
            if ant_err:
                errors.append(f"bullets.{section}[{i}] ({bid}) {ant_err}")

    # Skills char limits
    for key in REQUIRED_SKILLS:
        val = result.get("skills", {}).get(key, "")
        if len(val) > 200:
            errors.append(f"skills.{key} exceeds 200 chars ({len(val)})")

    # Summary char limit
    summary = result.get("summary", "")
    if len(summary) > 200:
        errors.append(f"summary exceeds 200 chars ({len(summary)})")

    # self_review failures (kept as a soft tripwire — real checks are above)
    failed = [k for k, v in result.get("self_review", {}).items() if v is False]
    if failed:
        errors.append(f"self_review failures: {failed}")

    # selection_log audit: ids referenced should be valid SOMEWHERE (loose check)
    all_valid_ids = set().union(*valid_by_section.values()) if valid_by_section else set()
    for entry in result.get("selection_log", []):
        pid = entry.get("picked_id", "")
        if pid and pid not in all_valid_ids:
            errors.append(
                f"selection_log contains ID not in candidates: {pid!r} "
                f"(section={entry.get('section')}, topic={entry.get('topic')})"
            )

    # Voice variety from bullet ids (deterministic)
    errors.extend(_check_voice_variety(result, id_lookup))

    return errors


def _strip_fences(raw: str) -> str:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return raw


# ── Public API ────────────────────────────────────────────────────────────────

def select(
    jd_analysis: dict,
    ranked_candidates: dict,
    skills_raw: str,
) -> dict:
    client = get_client()

    # Strip score breakdowns from candidates — 2B only needs id/text/voice.
    # Reduces payload by ~35%, critical for CLI-based invocation.
    def _slim(candidates: dict) -> dict:
        out = {}
        for section, topics in candidates.items():
            out[section] = {}
            for topic, data in topics.items():
                out[section][topic] = {
                    "allocated_bullets": data["allocated_bullets"],
                    "candidates": [
                        {"id": c["id"], "text": c["text"], "voice": c["voice"]}
                        for c in data["candidates"]
                    ],
                }
        return out

    # Also strip internal fields from jd_analysis not needed by 2B
    jd_slim = {k: v for k, v in jd_analysis.items() if k != "_jd_hash"}

    initial_user = json.dumps(
        {
            "jd_analysis":       jd_slim,
            "ranked_candidates": _slim(ranked_candidates),
            "skills_raw":        skills_raw,
        },
        ensure_ascii=False,
        separators=(",", ":"),  # compact JSON, no whitespace
    )

    # Conversation grows across retries — attempt 2 sees attempt 1's output and the
    # exact validator errors, instead of re-rolling the dice on the same input.
    messages: list[dict] = [{"role": "user", "content": initial_user}]
    last_errors: list[str] = []
    result: dict = {}

    for attempt in range(2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        raw_text = response.content[0].text.strip()
        raw = _strip_fences(raw_text)

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            last_errors = [f"Invalid JSON: {e}"]
        else:
            last_errors = _validate(result, ranked_candidates)

        if not last_errors:
            break

        if attempt == 0:
            print("[resume_selector] attempt 1 failed validation — feeding errors back to Claude:")
            for e in last_errors:
                print(f"  - {e}")
            messages.append({"role": "assistant", "content": raw_text})
            messages.append({
                "role": "user",
                "content": (
                    "Your previous output failed deterministic validation. "
                    "Fix ONLY the issues listed below and re-emit the COMPLETE JSON. "
                    "Keep every passing bullet, skill, summary, etc. byte-identical. "
                    "Do not narrate.\n\nErrors:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                ),
            })

    if last_errors:
        raise ValueError(
            "Resume Selector validation failed after 2 attempts:\n"
            + "\n".join(f"  - {e}" for e in last_errors)
        )

    SCRATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCRATCH_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[resume_selector] scratch -> {SCRATCH_FILE}")

    if result.get("flags"):
        print("[resume_selector] flags (review before submitting):")
        for f in result["flags"]:
            print(f"  ! {f}")

    print("\n[resume_selector] selection log:")
    for entry in result.get("selection_log", []):
        print(
            f"  [{entry.get('section')} / {entry.get('topic')}] "
            f"{entry.get('picked_id')} — {entry.get('reason')}"
        )

    return result
