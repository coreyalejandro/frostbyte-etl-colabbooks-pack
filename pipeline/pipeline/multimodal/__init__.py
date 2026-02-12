"""
Multi-modal document processing: images, audio, video.
Reference: Enhancement #9 PRD - Multi-Modal Document Support.
"""
from .detector import detect_modality

__all__ = ["detect_modality"]
