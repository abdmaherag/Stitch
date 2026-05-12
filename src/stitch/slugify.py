"""Company-name → filesystem-safe slug."""

from __future__ import annotations

import re
import unicodedata


def slugify(name: str) -> str:
    """Lowercase, ASCII-only, hyphenated, no leading/trailing hyphens.

    Used for `.tmp/<slug>/` and `out/<slug>-<date>/` directory names so
    different companies' artifacts never collide on the filesystem.

    Examples:
        "Acme Industries"  -> "acme-industries"
        "Goldman Sachs"    -> "goldman-sachs"
        "  ACME!  "        -> "acme"
        "Müller & Co."     -> "muller-co"
    """
    if not name or not name.strip():
        raise ValueError("Company name cannot be empty.")

    ascii_only = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = hyphenated.strip("-")

    if not stripped:
        raise ValueError(f"Company name {name!r} produced an empty slug after normalization.")

    return stripped
