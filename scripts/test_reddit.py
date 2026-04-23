"""Test Reddit crawler directly.

Run: python test_reddit.py
"""
import os
import sys
import asyncio
import logging

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

# Configure logging to see all messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_reddit_crawler():
    """Test the Reddit crawler with detailed output."""
    from crawlers.apify_runner import RedditCrawler

    print("\n" + "="*60)
    print("Testing Reddit Crawler")
    print("="*60)

    # Note: Reddit crawler uses public JSON API, no token needed
    print("[OK] Reddit crawler uses public JSON API (no Apify token required)")

    try:
        crawler = RedditCrawler()
        print("[OK] RedditCrawler initialized")

        # Run with config
        config = {"max_posts": 100}
        print(f"\nRunning crawler with config: {config}")
        print("-"*40)

        result = await crawler.run(config)

        print("-"*40)
        print(f"\nResult:")
        print(f"  run_id: {result.get('run_id')}")
        print(f"  items_crawled: {result.get('items_crawled')}")
        print(f"  items_new: {result.get('items_new')}")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_reddit_crawler())
