"""Small, dependency free text processing used by the intelligent features.

Everything runs locally in plain Python (no incident data leaves the server).
The approach is transparent: normalise -> map synonyms -> compare token sets.
"""
import re

STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were", "be", "been",
    "my", "our", "we", "i", "me", "it", "its", "this", "that", "and", "or", "with", "from", "by",
    "as", "has", "have", "had", "do", "does", "did", "not", "no", "make", "making", "get", "getting",
    "application", "app", "system", "service", "please", "help", "issue", "problem", "when", "while",
    "all", "some", "any", "now", "again", "still", "since", "after", "before", "user", "users",
    "try", "trying", "tried", "using", "use", "can", "will", "very", "also", "than", "then", "so",
}

# Words that mean the same thing for the purpose of spotting duplicates.
SYNONYM_GROUPS = {
    "fail": ["unavailable", "down", "fail", "failing", "failed", "failure", "error", "outage",
             "broken", "crash", "crashed", "crashing", "unable", "cannot", "cant", "unreachable",
             "stuck", "timeout", "unresponsive", "offline", "inaccessible", "denied"],
    "payment": ["payment", "pay", "transaction", "checkout", "billing", "paying"],
    "login": ["login", "logon", "signin", "authenticate", "authentication", "auth", "sso",
              "password", "credential", "credentials", "logins"],
    "slow": ["slow", "slowness", "sluggish", "lag", "laggy", "latency", "delay", "delayed", "lagging"],
    "wifi": ["wifi", "wireless", "wlan"],
    "email": ["email", "mail", "outlook", "mailbox", "inbox"],
    "print": ["print", "printer", "printing", "jam", "jammed", "toner"],
    "storage": ["storage", "disk", "drive", "quota", "space"],
    "database": ["database", "db", "sql", "query", "deadlock"],
}
_CANON = {word: canon for canon, words in SYNONYM_GROUPS.items() for word in words}

_PHRASES = [
    (re.compile(r"\bwi[\s-]?fi\b"), "wifi"),
    (re.compile(r"\b(?:not|isn't|isnt|aren't|stopped|no longer|won't|wont|doesn't|doesnt)\s+(?:working|work|loading|responding|opening)\b"), "fail"),
    (re.compile(r"\b(?:can't|can not|cannot|unable to|couldn't|could not)\b"), "fail"),
    (re.compile(r"\blog[\s-]?in\b"), "login"),
    (re.compile(r"\bsign[\s-]?in\b"), "login"),
    (re.compile(r"\be-?mail\b"), "email"),
]
_WORD = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    text = (text or "").lower().replace("’", "'")
    for pattern, repl in _PHRASES:
        text = pattern.sub(f" {repl} ", text)
    return text


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix) and not word.endswith("ss"):
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> set:
    """Return the canonical token set of a piece of text."""
    out = set()
    for raw in _WORD.findall(normalize(text)):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        canon = _CANON.get(raw) or _CANON.get(_stem(raw)) or _stem(raw)
        if canon in STOPWORDS:
            continue
        out.add(canon)
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def keyword_hits(text_title: str, text_desc: str, keyword: str) -> int:
    """Return 2 when the keyword is found in the title, 1 for the description, else 0."""
    kw = " ".join(_WORD.findall(normalize(keyword)))
    if not kw:
        return 0

    def found(text: str) -> bool:
        norm = " " + " ".join(_WORD.findall(normalize(text))) + " "
        if " " in kw:
            return f" {kw} " in norm
        if len(kw) >= 4:
            return any(tok == kw or tok.startswith(kw) for tok in norm.split())
        return f" {kw} " in norm

    if found(text_title):
        return 2
    if found(text_desc):
        return 1
    return 0
