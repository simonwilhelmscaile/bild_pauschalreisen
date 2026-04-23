"""Embedding service using Google Gemini text-embedding-004."""
import logging
from typing import List

from services.gemini import get_embedding_client, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed (will be truncated if too long)

    Returns:
        List of 768 floats representing the embedding
    """
    genai = get_embedding_client()

    # Truncate to stay within token limits (~10000 chars for safety)
    if len(text) > 10000:
        text = text[:10000]

    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768
    )
    return result['embedding']


def generate_embeddings_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        batch_size: Number of texts per API call

    Returns:
        List of embeddings in same order as input texts
    """
    genai = get_embedding_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Truncate each text
        batch = [t[:10000] if len(t) > 10000 else t for t in batch]

        # Gemini embed_content can take a list
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch,
            task_type="retrieval_document",
            output_dimensionality=768
        )
        # Result is a list of embeddings when content is a list
        all_embeddings.extend(result['embedding'])

    return all_embeddings


def backfill_embeddings(batch_size: int = 100) -> dict:
    """Backfill embeddings for items with NULL embedding.

    Args:
        batch_size: Number of items to process per batch

    Returns:
        Dict with stats: {processed: int, failed: int, skipped: int}
    """
    from db.client import get_beurer_supabase

    client = get_beurer_supabase()
    stats = {"processed": 0, "failed": 0, "skipped": 0}

    while True:
        # Fetch items without embeddings
        result = client.table("social_items") \
            .select("id, title, content, question_content") \
            .is_("embedding", "null") \
            .limit(batch_size) \
            .execute()

        if not result.data:
            break

        items = result.data
        logger.info(f"Processing {len(items)} items for embeddings")

        # Prepare texts (combine title and content, prefer question_content)
        texts = []
        for item in items:
            title = item.get('title', '')
            question_content = item.get('question_content')
            content = item.get('content', '')
            if question_content:
                text = f"{title} {question_content}".strip()
            else:
                text = f"{title} {content}".strip()
            if not text:
                stats["skipped"] += 1
                texts.append("")
            else:
                texts.append(text)

        try:
            embeddings = generate_embeddings_batch([t for t in texts if t], batch_size=batch_size)

            # Update items with embeddings
            embedding_idx = 0
            for item, text in zip(items, texts):
                if not text:
                    continue
                try:
                    embedding = embeddings[embedding_idx]
                    embedding_idx += 1

                    client.table("social_items") \
                        .update({"embedding": embedding}) \
                        .eq("id", item["id"]) \
                        .execute()
                    stats["processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to update item {item['id']}: {e}")
                    stats["failed"] += 1

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            stats["failed"] += len(items)

    logger.info(f"Backfill complete: {stats}")
    return stats


def embed_text_for_search(text: str) -> List[float]:
    """Generate embedding for a search query.

    Uses retrieval_query task type for better search results.
    """
    genai = get_embedding_client()

    # Truncate if needed
    if len(text) > 10000:
        text = text[:10000]

    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=768
    )
    return result['embedding']
