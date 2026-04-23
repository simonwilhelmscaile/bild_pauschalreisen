"""Crawlers package.

Organized by tool:
- firecrawl_runner.py: GutefrageCrawler, HealthForumsCrawler
- apify_runner.py: AmazonCrawler, RedditCrawler, YouTubeCrawler, TikTokCrawler, InstagramCrawler, TwitterCrawler
- serper_runner.py: SerperDiscoveryCrawler, SerperBrandMentionsCrawler
"""
from crawlers.firecrawl_runner import GutefrageCrawler, HealthForumsCrawler
from crawlers.apify_runner import (
    AmazonCrawler,
    RedditCrawler,
    YouTubeCrawler,
    TikTokCrawler,
    InstagramCrawler,
    TwitterCrawler,
)
from crawlers.serper_runner import (
    SerperDiscoveryCrawler,
    SerperBrandMentionsCrawler,
)
from crawlers.exa_runner import ExaNewsCrawler

__all__ = [
    # Firecrawl-based
    "GutefrageCrawler",
    "HealthForumsCrawler",
    # Apify-based
    "AmazonCrawler",
    "RedditCrawler",
    "YouTubeCrawler",
    "TikTokCrawler",
    "InstagramCrawler",
    "TwitterCrawler",
    # Serper-based
    "SerperDiscoveryCrawler",
    "SerperBrandMentionsCrawler",
    # Exa-based
    "ExaNewsCrawler",
]
