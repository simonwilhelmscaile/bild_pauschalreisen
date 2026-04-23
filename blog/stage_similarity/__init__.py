"""
Stage Similarity: Content Similarity Check

Detects content cannibalization by comparing generated article
against previously generated articles using character shingles.

Features:
- Character-level shingling for language-agnostic similarity
- Batch session memory (in-memory storage for current session)
- Non-blocking: logs warnings but doesn't block publication
"""

from .similarity_check import (
    run_similarity_check,
    clear_batch_memory,
    get_batch_memory_stats,
    SimilarityReport,
)

__all__ = [
    "run_similarity_check",
    "clear_batch_memory",
    "get_batch_memory_stats",
    "SimilarityReport",
]
