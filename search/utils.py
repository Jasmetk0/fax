import unicodedata

__all__ = ["normalize", "levenshtein_max1", "fuzzy1_token_match"]


def normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.casefold()


def levenshtein_max1(a: str, b: str) -> bool:
    """Return True if edit distance between ``a`` and ``b`` is at most 1."""

    if abs(len(a) - len(b)) > 1:
        return False
    if a == b:
        return True

    if len(a) > len(b):
        a, b = b, a

    i = j = 0
    mismatches = 0
    while i < len(a) and j < len(b):
        if a[i] != b[j]:
            mismatches += 1
            if mismatches > 1:
                return False
            if len(a) == len(b):
                i += 1
            # always advance the longer string
            j += 1
        else:
            i += 1
            j += 1

    if j < len(b) or i < len(a):
        mismatches += 1

    return mismatches <= 1


def fuzzy1_token_match(q_tok: str, t_tok: str) -> bool:
    """Return True for tokens that match exactly or with distance of 1."""

    if not q_tok or not t_tok:
        return False
    if q_tok == t_tok:
        return True
    if len(q_tok) >= 4 and len(t_tok) >= 4:
        return levenshtein_max1(q_tok, t_tok)
    return False
