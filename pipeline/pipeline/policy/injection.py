"""
Injection defense per DOCUMENT_SAFETY Section 1.
Pattern scanner + heuristic scorer.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class PatternMatch:
    category: str
    count: int
    severity: float  # 0.0-1.0


# Pattern definitions: (regex, category, severity) per DOCUMENT_SAFETY 1.2
INJECTION_PATTERNS: list[tuple[str, str, float]] = [
    (r"(?i)(ignore\s+previous\s+instructions?|forget\s+(everything\s+)?above)", "direct_instruction_override", 1.0),
    (r"(?i)(you\s+are\s+now\s+(a\s+)?|act\s+as\s+if\s+you\s+have\s+no\s+restrictions)", "role_assumption", 1.0),
    (r"(?i)(repeat\s+your\s+system\s+prompt|what\s+are\s+your\s+instructions)", "system_prompt_leakage", 0.8),
    (r"(?i)(```\s*system|#{1,6}\s*instructions?\s*:)|<\|im_start\|>\s*system", "delimiter_injection", 1.0),
    (r"(?i)(disregard\s+(all\s+)?(previous|above)|override\s+(all\s+)?(previous|above)|new\s+instructions?\s*:)", "generic_override", 1.0),
    (r"(?i)(you\s+have\s+no\s+(content\s+)?policy|ignore\s+safety)", "jailbreak_attempts", 1.0),
    (r"(?i)in\s+your\s+next\s+response,?\s*(always|you\s+must)", "multi_turn_manipulation", 0.8),
    (r"(?i)(decode\s+this\s*:|execute\s*:\s*[A-Za-z0-9+/=]{20,})", "obfuscation_markers", 0.8),
    (r"(?i)(do\s+not\s+mention|never\s+reveal|always\s+say|you\s+must\s+respond)", "instruction_like_imperative", 0.7),
    (r"(?i)(your\s+new\s+role|from\s+now\s+on\s+you)", "second_person_command", 0.7),
]

INVISIBLE_CHARS_RE = re.compile(r"[\u200B\u200C\u200D\u200E\u200F\u202A\u202B\u202C\u202D\u202E\u2060\uFEFF\u034F]")


def scan_injection_patterns(text: str) -> list[PatternMatch]:
    """Scan text for injection patterns. Returns list of PatternMatch."""
    matches: list[PatternMatch] = []
    seen_cats: dict[str, tuple[int, float]] = {}

    for pattern, category, severity in INJECTION_PATTERNS:
        try:
            m = re.findall(pattern, text)
            count = len(m)
            if count > 0:
                prev = seen_cats.get(category, (0, 0.0))
                seen_cats[category] = (prev[0] + count, max(prev[1], severity))
        except re.error:
            continue

    for cat, (count, sev) in seen_cats.items():
        matches.append(PatternMatch(category=cat, count=count, severity=sev))

    return matches


def count_invisible_chars(text: str) -> int:
    """Count invisible/control characters per DOCUMENT_SAFETY 1.2."""
    return len(INVISIBLE_CHARS_RE.findall(text))


def has_instruction_like_structure(text: str) -> bool:
    """Check for imperative + second person structure (weight 0.2)."""
    ilk = re.search(r"(?i)(you\s+must|do\s+not\s+\w+|never\s+\w+|always\s+\w+)", text)
    return ilk is not None


def compute_injection_score(text: str, matches: list[PatternMatch]) -> float:
    """
    Heuristic score 0.0-1.0 per DOCUMENT_SAFETY 1.3.
    Factors: pattern match (0.4), invisible ratio (0.3), instruction-like (0.2), length anomaly (0.1).
    """
    base = 0.0
    for m in matches:
        contrib = m.severity * min(m.count * 0.2, 1.0)
        base += contrib
    base = min(base * 0.4, 0.4)

    n_chars = len(text) or 1
    invisible_count = count_invisible_chars(text)
    invisible_ratio = invisible_count / n_chars
    invisible_contrib = min(invisible_ratio * 10, 0.3)

    imperative_contrib = 0.2 if has_instruction_like_structure(text) else 0.0

    length_contrib = 0.1 if len(matches) >= 3 and len(text) > 500 else 0.0

    return min(base + invisible_contrib + imperative_contrib + length_contrib, 1.0)
