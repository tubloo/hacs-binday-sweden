from __future__ import annotations

import re


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Return a stable, HA-entity-safe slug."""
    value = value.strip().lower()
    value = value.replace("å", "a").replace("ä", "a").replace("ö", "o")
    value = _NON_ALNUM_RE.sub("_", value).strip("_")
    return value or "unknown"

