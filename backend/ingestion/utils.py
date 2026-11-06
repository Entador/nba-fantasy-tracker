import re
import unicodedata

# Punctuation that differs between data sources for the same player:
# "Ernest Udeh, Jr." (nba_api) vs "Ernest Udeh Jr." (injury report),
# "De'Aaron Fox" vs "DeAaron Fox". Hyphens become spaces so
# "Gilgeous-Alexander" and "Gilgeous Alexander" collapse to one key.
_DROP_PUNCT_RE = re.compile(r"[.,'’ʼ]")
_TO_SPACE_RE = re.compile(r"[-‐-―]")


def normalize_name(name: str) -> str:
    """Normalize a player or team name for matching across data sources.

    Lowercases, strips accents, drops punctuation that sources disagree on,
    and collapses whitespace. Matching only — never for display.
    """
    # Remove accents: é -> e, ć -> c, ū -> u, etc.
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = _DROP_PUNCT_RE.sub("", ascii_name)
    ascii_name = _TO_SPACE_RE.sub(" ", ascii_name)
    return " ".join(ascii_name.lower().split())
