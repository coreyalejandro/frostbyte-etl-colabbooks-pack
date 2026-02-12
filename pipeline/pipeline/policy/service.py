"""
Policy service: run all gates, produce policy-enriched chunks for embedding.
Per POLICY_ENGINE_PLAN Section 7.
"""
from __future__ import annotations

from typing import Sequence

from pipeline.parsing.models import CanonicalStructuredDocument, Chunk

from .gates import Gate1Result, Gate3Result, gate1_pii, gate2_classification, gate3_injection
from .models import ChunkOffsets, PolicyEnrichedChunk


def run_policy_gates(
    doc: CanonicalStructuredDocument,
    tenant_config: dict,
    original_filename: str | None = None,
) -> tuple[list[PolicyEnrichedChunk], int, bool]:
    """
    Run Gate 1 → Gate 2 → Gate 3 on each chunk.
    Returns (passing_chunks, quarantined_count, document_blocked).
    document_blocked = True if Gate 1 BLOCK on any chunk (per-doc quarantine).
    """
    passing: list[PolicyEnrichedChunk] = []
    quarantined_count = 0
    document_blocked = False
    any_injection_quarantined = False

    # Sample text for classification (first few chunks)
    sample_parts = [c.text for c in doc.chunks[:5]]
    doc_text_sample = " ".join(sample_parts)[:3000]
    classification, class_confidence = gate2_classification(
        doc_text_sample, original_filename, tenant_config
    )
    classifier_version = "rule-v1"

    per_document_quarantine = tenant_config.get("injection_per_document_quarantine", False)

    for chunk in doc.chunks:
        text = chunk.text

        # Gate 1: PII
        g1 = gate1_pii(text, tenant_config)
        if g1.blocked:
            document_blocked = True
            quarantined_count += 1
            continue

        if g1.modified_text is not None:
            text = g1.modified_text

        # Gate 3: Injection
        g3 = gate3_injection(text, tenant_config)
        if g3.quarantined:
            quarantined_count += 1
            any_injection_quarantined = True
            continue

        # Build policy-enriched metadata
        metadata: dict = {
            "pii_scan_result": g1.pii_scan_result,
            "pii_types_found": g1.pii_types_found,
            "pii_action_taken": g1.pii_action_taken,
            "classification": classification,
            "classification_confidence": class_confidence,
            "classifier_version": classifier_version,
            "human_override": False,
            "injection_score": g3.score,
            "injection_patterns_matched": g3.patterns_matched,
            "injection_action_taken": g3.action,
        }

        passing.append(
            PolicyEnrichedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=doc.doc_id,
                tenant_id=doc.tenant_id,
                text=text,
                metadata=metadata,
                offsets=ChunkOffsets(
                    page=chunk.page,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                ),
                element_type=chunk.element_type,
                section_title=chunk.metadata.section_title if chunk.metadata else None,
            )
        )

    # Per-document quarantine: if any chunk was injection-quarantined, drop all passing
    if per_document_quarantine and any_injection_quarantined:
        passing = []
        quarantined_count = len(doc.chunks)

    return passing, quarantined_count, document_blocked
