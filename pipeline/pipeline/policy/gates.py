"""
Policy gates: PII, classification, injection.
Per POLICY_ENGINE_PLAN Sections 2-4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from . import injection
from .injection import PatternMatch, compute_injection_score, scan_injection_patterns
from .models import (
    PRESIDIO_TO_PII_CODE,
    PII_POLICY_BLOCK,
    PII_POLICY_FLAG,
    PII_POLICY_REDACT,
    DEFAULT_PII_TYPES,
    CLASSIFICATION_CATEGORIES,
)


@dataclass
class Gate1Result:
    passed: bool
    blocked: bool
    pii_types_found: list[str]
    pii_scan_result: Literal["clean", "pii_found", "redacted", "blocked"]
    pii_action_taken: Literal["none", "redacted", "flagged", "blocked"]
    modified_text: str | None = None


def _get_pii_analyzer():
    try:
        from presidio_analyzer import AnalyzerEngine
        return AnalyzerEngine()
    except ImportError:
        return None


def _get_pii_anonymizer():
    try:
        from presidio_anonymizer import AnonymizerEngine
        return AnonymizerEngine()
    except ImportError:
        return None


def _presidio_to_pii_code(entity_type: str) -> str:
    return PRESIDIO_TO_PII_CODE.get(entity_type, entity_type)


def gate1_pii(
    text: str,
    tenant_config: dict,
) -> Gate1Result:
    """
    Gate 1: PII detection. REDACT/FLAG/BLOCK per tenant config.
    """
    pii_policy = tenant_config.get("pii_policy", "FLAG")
    pii_types = tenant_config.get("pii_types", DEFAULT_PII_TYPES)

    # Map our codes to Presidio entities (subset we care about)
    presidio_entities = []
    code_to_presidio = {v: k for k, v in PRESIDIO_TO_PII_CODE.items()}
    for code in pii_types:
        pe = code_to_presidio.get(code, code)
        if pe:
            presidio_entities.append(pe)

    if not presidio_entities:
        presidio_entities = ["US_SSN", "DATE_TIME", "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"]

    analyzer = _get_pii_analyzer()
    if analyzer is None:
        return Gate1Result(
            passed=True,
            blocked=False,
            pii_types_found=[],
            pii_scan_result="clean",
            pii_action_taken="none",
        )

    results = analyzer.analyze(text=text, entities=presidio_entities, language="en")
    pii_types_found = list({_presidio_to_pii_code(r.entity_type) for r in results})

    if not pii_types_found:
        return Gate1Result(
            passed=True,
            blocked=False,
            pii_types_found=[],
            pii_scan_result="clean",
            pii_action_taken="none",
        )

    if pii_policy == PII_POLICY_BLOCK:
        return Gate1Result(
            passed=False,
            blocked=True,
            pii_types_found=pii_types_found,
            pii_scan_result="blocked",
            pii_action_taken="blocked",
        )

    if pii_policy == PII_POLICY_REDACT:
        anonymizer = _get_pii_anonymizer()
        if anonymizer:
            anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
            # Replace <ENTITY> with [REDACTED:ENTITY]
            modified = anonymized.text
            import re
            modified = re.sub(r"<(\w+)>", r"[REDACTED:\1]", modified)
            return Gate1Result(
                passed=True,
                blocked=False,
                pii_types_found=pii_types_found,
                pii_scan_result="redacted",
                pii_action_taken="redacted",
                modified_text=modified,
            )

    # FLAG or fallback
    return Gate1Result(
        passed=True,
        blocked=False,
        pii_types_found=pii_types_found,
        pii_scan_result="pii_found",
        pii_action_taken="flagged",
    )


def gate2_classification(
    doc_text_sample: str,
    filename: str | None,
    tenant_config: dict,
) -> tuple[str, float]:
    """
    Gate 2: Document classification. Rule-based + optional ML.
    Returns (classification, confidence).
    """
    threshold = float(tenant_config.get("classification_threshold", 0.7))
    rules: list[tuple[str, float, bool]] = []

    # Rule-based: filename
    if filename:
        fn = filename.lower()
        if "contract" in fn or "agreement" in fn:
            rules.append(("contract", 0.85, True))
        if "invoice" in fn or "bill" in fn:
            rules.append(("invoice", 0.85, True))
        if "sop" in fn or "procedure" in fn:
            rules.append(("SOP", 0.85, True))
        if "policy" in fn:
            rules.append(("policy", 0.85, True))
        if "legal" in fn or "court" in fn or "filing" in fn:
            rules.append(("legal_filing", 0.85, True))
        if "letter" in fn or "email" in fn or "correspondence" in fn:
            rules.append(("correspondence", 0.75, True))

    # Rule-based: header keywords
    sample = (doc_text_sample or "")[:2000].upper()
    if "AGREEMENT" in sample or "CONTRACT" in sample:
        rules.append(("contract", 0.8, True))
    if "INVOICE" in sample or "BILL TO" in sample:
        rules.append(("invoice", 0.8, True))
    if "STANDARD OPERATING PROCEDURE" in sample or "SOP" in sample:
        rules.append(("SOP", 0.8, True))
    if "POLICY" in sample and "DOCUMENT" in sample:
        rules.append(("policy", 0.75, True))

    if rules:
        # Take highest confidence match
        best = max(rules, key=lambda x: x[1])
        return best[0], best[1]

    return "other", 0.5


@dataclass
class Gate3Result:
    passed: bool
    quarantined: bool
    score: float
    patterns_matched: list[str]
    action: Literal["pass", "flag", "quarantine"]


def gate3_injection(
    text: str,
    tenant_config: dict,
) -> Gate3Result:
    """
    Gate 3: Injection defense. PASS/FLAG/QUARANTINE per score thresholds.
    """
    flag_threshold = float(tenant_config.get("injection_flag_threshold", 0.3))
    quarantine_threshold = float(tenant_config.get("injection_quarantine_threshold", 0.7))

    matches = scan_injection_patterns(text)
    score = compute_injection_score(text, matches)
    patterns_matched = list({m.category for m in matches})

    if score < flag_threshold:
        return Gate3Result(
            passed=True,
            quarantined=False,
            score=score,
            patterns_matched=[],
            action="pass",
        )

    if score >= quarantine_threshold:
        return Gate3Result(
            passed=False,
            quarantined=True,
            score=score,
            patterns_matched=patterns_matched,
            action="quarantine",
        )

    return Gate3Result(
        passed=True,
        quarantined=False,
        score=score,
        patterns_matched=patterns_matched,
        action="flag",
    )
