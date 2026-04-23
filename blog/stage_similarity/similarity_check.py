"""
Stage Similarity: Content Similarity Check

Detects content cannibalization by comparing generated article
against previously generated articles using character shingles.

Features:
- Character-level shingling for language-agnostic similarity
- Batch session memory (in-memory storage for current session)
- Non-blocking: logs warnings but doesn't block publication

Input:
  - Article content (ArticleOutput or dict)

Output:
  - SimilarityReport with similarity analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)

# Similarity thresholds (matching TypeScript defaults)
CHAR_SIMILARITY_THRESHOLD = 0.65  # 65% character similarity = too similar
SHINGLE_SIZE = 5  # 5-character shingles


@dataclass
class SimilarArticle:
    """Reference to a similar article."""
    job_id: str
    similarity: float


@dataclass
class SimilarityReport:
    """Result of similarity check."""
    job_id: str
    similarity_score: float
    is_too_similar: bool
    similar_articles: List[SimilarArticle] = field(default_factory=list)
    check_method: str = "character_shingles"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BatchSimilarityMemory:
    """
    In-memory storage for batch similarity checking.
    Stores article content from current generation session.
    """

    def __init__(self):
        self._articles: Dict[str, str] = {}

    def add(self, job_id: str, content: str) -> None:
        """Add article content to memory."""
        self._articles[job_id] = content

    def get_all(self) -> Dict[str, str]:
        """Get all stored articles."""
        return self._articles

    def clear(self) -> None:
        """Clear all stored articles."""
        self._articles.clear()

    def size(self) -> int:
        """Get number of stored articles."""
        return len(self._articles)


# Global batch memory (shared across all similarity checks in current session)
_batch_memory = BatchSimilarityMemory()


def generate_shingles(text: str, size: int) -> Set[str]:
    """
    Generate character shingles from text.

    Shingles are overlapping n-character substrings used for
    fuzzy text comparison.

    Example: "hello" with size=3 → {"hel", "ell", "llo"}
    """
    shingles = set()
    # Normalize: lowercase and collapse whitespace
    normalized = " ".join(text.lower().split())

    for i in range(len(normalized) - size + 1):
        shingles.add(normalized[i:i + size])

    return shingles


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """
    Calculate Jaccard similarity between two sets.

    Jaccard similarity = (intersection / union)
    Returns value between 0 (no overlap) and 1 (identical)
    """
    if len(set1) == 0 and len(set2) == 0:
        return 1.0
    if len(set1) == 0 or len(set2) == 0:
        return 0.0

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union)


def extract_article_text(article_data: Any) -> str:
    """
    Extract article content for similarity comparison.

    Combines all text fields into single string for analysis.
    """
    parts: List[str] = []

    # Handle dict or object
    def get_value(key: str) -> Optional[str]:
        if isinstance(article_data, dict):
            return article_data.get(key)
        return getattr(article_data, key, None)

    # Add main content fields
    if headline := get_value("headline"):
        parts.append(headline)
    if intro := get_value("intro"):
        parts.append(intro)
    if direct_answer := get_value("direct_answer"):
        parts.append(direct_answer)

    # Add all sections
    for i in range(1, 10):
        title_key = f"section_{str(i).zfill(2)}_title"
        content_key = f"section_{str(i).zfill(2)}_content"

        if title := get_value(title_key):
            parts.append(title)
        if content := get_value(content_key):
            parts.append(content)

    # Add FAQ
    for i in range(1, 7):
        q_key = f"faq_{str(i).zfill(2)}_question"
        a_key = f"faq_{str(i).zfill(2)}_answer"

        if question := get_value(q_key):
            parts.append(question)
        if answer := get_value(a_key):
            parts.append(answer)

    # Add PAA
    for i in range(1, 5):
        q_key = f"paa_{str(i).zfill(2)}_question"
        a_key = f"paa_{str(i).zfill(2)}_answer"

        if question := get_value(q_key):
            parts.append(question)
        if answer := get_value(a_key):
            parts.append(answer)

    return " ".join(parts)


def check_similarity(job_id: str, article_text: str) -> SimilarityReport:
    """
    Check similarity against all articles in batch memory.
    """
    current_shingles = generate_shingles(article_text, SHINGLE_SIZE)
    similar_articles: List[SimilarArticle] = []
    max_similarity = 0.0

    # Compare against all articles in batch memory
    for other_job_id, other_text in _batch_memory.get_all().items():
        if other_job_id == job_id:
            continue  # Skip self

        other_shingles = generate_shingles(other_text, SHINGLE_SIZE)
        similarity = jaccard_similarity(current_shingles, other_shingles)

        if similarity > 0.1:  # Only track if > 10% similar
            similar_articles.append(SimilarArticle(
                job_id=other_job_id,
                similarity=round(similarity, 2),
            ))

        max_similarity = max(max_similarity, similarity)

    # Sort by similarity (descending)
    similar_articles.sort(key=lambda x: x.similarity, reverse=True)

    is_too_similar = max_similarity >= CHAR_SIMILARITY_THRESHOLD

    return SimilarityReport(
        job_id=job_id,
        similarity_score=round(max_similarity, 2),
        is_too_similar=is_too_similar,
        similar_articles=similar_articles[:5],  # Top 5 most similar
        check_method="character_shingles",
    )


def run_similarity_check(
    job_id: str,
    article_data: Any,
    add_to_memory: bool = True,
) -> Optional[SimilarityReport]:
    """
    Run content similarity check.

    Non-blocking similarity detection.
    Logs warnings if content is too similar to previous articles.

    Args:
        job_id: Unique identifier for this article
        article_data: Article content (ArticleOutput or dict)
        add_to_memory: Whether to add to batch memory for future comparisons

    Returns:
        SimilarityReport or None if check cannot be performed
    """
    logger.info("[Similarity] Starting Content Similarity Check")

    if not article_data:
        logger.info("[Similarity] No article data available, skipping")
        return None

    try:
        # Extract article text
        article_text = extract_article_text(article_data)

        if not article_text or len(article_text) < 100:
            logger.info("[Similarity] Article text too short, skipping")
            return None

        # Check similarity
        report = check_similarity(job_id, article_text)

        # Store in batch memory for future comparisons
        if add_to_memory:
            _batch_memory.add(job_id, article_text)

        # Log results
        logger.info(f"[Similarity] Check complete:")
        logger.info(f"[Similarity]   - Method: {report.check_method}")
        logger.info(f"[Similarity]   - Max similarity: {report.similarity_score * 100:.1f}%")
        logger.info(f"[Similarity]   - Compared against: {_batch_memory.size() - 1} articles")

        if report.is_too_similar:
            logger.warning(
                f"[Similarity] ⚠️ WARNING: Content similarity ({report.similarity_score * 100:.1f}%) "
                f"exceeds threshold ({CHAR_SIMILARITY_THRESHOLD * 100:.1f}%)"
            )
            logger.warning("[Similarity]   Similar articles:")
            for similar in report.similar_articles:
                logger.warning(f"[Similarity]     - {similar.job_id}: {similar.similarity * 100:.1f}%")
        else:
            logger.info("[Similarity] ✅ Content is unique (similarity below threshold)")

        return report

    except Exception as e:
        # Non-blocking: log error but don't fail the pipeline
        logger.error(f"[Similarity] Similarity check failed: {e}")
        logger.info("[Similarity] Continuing pipeline (non-blocking stage)")
        return None


def clear_batch_memory() -> None:
    """Clear batch memory (useful for testing or starting new batch session)."""
    _batch_memory.clear()
    logger.info("[Similarity] Batch memory cleared")


def get_batch_memory_stats() -> Dict[str, Any]:
    """Get batch memory stats."""
    return {
        "size": _batch_memory.size(),
        "job_ids": list(_batch_memory.get_all().keys()),
    }
