"""One-off script to run YouTube crawl directly (no HTTP server needed).

Usage:
    python run_youtube_crawl.py                    # Full crawl (all targets)
    python run_youtube_crawl.py --quick            # Quick test (first 2 targets only)
    python run_youtube_crawl.py --start 4 --count 3  # Targets 4-6 (0-indexed)
    python run_youtube_crawl.py --start 7            # Targets 7 onwards
"""
import os
import asyncio
import logging
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

from crawlers.apify_runner import YouTubeCrawler, YOUTUBE_TARGETS


def parse_args():
    args = sys.argv[1:]
    if "--quick" in args:
        return 0, 2
    start = 0
    count = len(YOUTUBE_TARGETS)
    for i, a in enumerate(args):
        if a == "--start" and i + 1 < len(args):
            start = int(args[i + 1])
        if a == "--count" and i + 1 < len(args):
            count = int(args[i + 1])
    return start, count


async def main():
    start, count = parse_args()
    import crawlers.apify_runner as mod
    original_targets = mod.YOUTUBE_TARGETS
    end = min(start + count, len(original_targets))
    mod.YOUTUBE_TARGETS = original_targets[start:end]

    print(f"Processing targets {start}-{end - 1} of {len(original_targets)} ({len(mod.YOUTUBE_TARGETS)} targets)")
    for i, t in enumerate(mod.YOUTUBE_TARGETS):
        print(f"  [{start + i}] {t}")

    crawler = YouTubeCrawler()
    result = await crawler.run({})

    mod.YOUTUBE_TARGETS = original_targets

    print(f"\n=== CRAWL RESULT ===")
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
