"""Run Serper brand crawler with full pipeline."""
import os, sys
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

import asyncio
import logging
from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

from crawlers import SerperBrandMentionsCrawler
from services.embedding import backfill_embeddings
from classification import backfill_classifications

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    print("=" * 60)
    print("STEP 1: Running Serper Brand Mentions Crawler")
    print("=" * 60)

    crawler = SerperBrandMentionsCrawler()
    result = await crawler.run({})  # Run all queries

    print(f"\nCrawl complete:")
    print(f"  Run ID: {result['run_id']}")
    print(f"  Items crawled: {result['items_crawled']}")
    print(f"  New items saved: {result['items_new']}")

    if result['items_new'] == 0:
        print("\nNo new items to process. Done.")
        return

    print("\n" + "=" * 60)
    print("STEP 2: Generating Embeddings")
    print("=" * 60)
    embed_stats = backfill_embeddings(batch_size=100)
    print(f"  Processed: {embed_stats['processed']}")
    print(f"  Failed: {embed_stats['failed']}")

    print("\n" + "=" * 60)
    print("STEP 3: Running Classifications")
    print("=" * 60)
    class_stats = backfill_classifications(batch_size=50)
    print(f"  Processed: {class_stats['processed']}")
    print(f"  Failed: {class_stats['failed']}")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
