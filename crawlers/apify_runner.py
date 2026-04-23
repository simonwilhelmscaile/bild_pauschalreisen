"""Apify crawlers for Amazon, Reddit, TikTok, YouTube, Instagram, and Twitter/X.

This module consolidates all Apify-based crawlers:
- AmazonCrawler: Amazon.de product reviews (Priority 1B)
- RedditCrawler: German health subreddits (Every 6h)
- YouTubeCrawler: Health-related video transcripts + comments (Weekly)
- TikTokCrawler: Health content (Weekly, low priority)
- InstagramCrawler: Health content with comment fetching (Weekly, low priority)
- TwitterCrawler: Twitter/X health device mentions (Weekly)
"""
import asyncio
import logging
import os
from typing import Any, Dict, List

import httpx

from crawlers.base_crawler import BaseCrawler
from utils.dates import parse_to_yyyy_mm_dd

logger = logging.getLogger(__name__)


# =============================================================================
# APIFY API CLIENT
# =============================================================================

class ApifyClient:
    """Shared Apify API client."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.apify.com/v2"

    async def run_actor(
        self,
        actor_id: str,
        input_data: Dict[str, Any],
        timeout_minutes: int = 5
    ) -> List[Dict]:
        """Run an Apify Actor and wait for results."""
        async with httpx.AsyncClient(timeout=300) as client:
            # Start the Actor run
            response = await client.post(
                f"{self.base_url}/acts/{actor_id}/runs",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json=input_data
            )
            response.raise_for_status()
            run_data = response.json()
            run_id = run_data["data"]["id"]

            logger.info(f"[apify] Started run {run_id} for actor {actor_id}")

            # Poll for completion
            max_polls = timeout_minutes * 12  # Check every 5 seconds
            for _ in range(max_polls):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{self.base_url}/actor-runs/{run_id}",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )
                status_resp.raise_for_status()
                status = status_resp.json()["data"]["status"]

                if status == "SUCCEEDED":
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    raise Exception(f"Apify run {run_id} failed with status: {status}")

            # Fetch results from dataset
            dataset_id = run_data["data"]["defaultDatasetId"]
            results_resp = await client.get(
                f"{self.base_url}/datasets/{dataset_id}/items",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
            results_resp.raise_for_status()
            return results_resp.json()


# =============================================================================
# AMAZON CRAWLER (Priority 1B)
# =============================================================================

# Beurer product ASINs on amazon.de
AMAZON_ASINS = [
    # ===========================================
    # BEURER BLOOD PRESSURE MONITORS (BM/BC Series)
    # ===========================================
    # Priority 1
    {"asin": "B01B4PKQL2", "name": "Beurer BM 27", "category": "blood_pressure"},
    {"asin": "B0DSW11C1S", "name": "Beurer BM 25", "category": "blood_pressure"},
    {"asin": "B09TLKKWQR", "name": "Beurer BM 81", "category": "blood_pressure"},
    # Priority 2
    {"asin": "B0CGZPYY5G", "name": "Beurer BM 53", "category": "blood_pressure"},
    {"asin": "B0CJ5S5H18", "name": "Beurer BM 64", "category": "blood_pressure"},
    {"asin": "B0854R382Z", "name": "Beurer BC 54", "category": "blood_pressure"},
    {"asin": "B09ZY5MQWH", "name": "Beurer BC 27", "category": "blood_pressure"},
    # Priority 3
    {"asin": "B07F1GDY9D", "name": "Beurer BM 54", "category": "blood_pressure"},
    {"asin": "B0DCBS5F6G", "name": "Beurer BM 59", "category": "blood_pressure"},
    {"asin": "B09CGV5K51", "name": "Beurer BM 96", "category": "blood_pressure"},
    # Priority 4 (legacy)
    {"asin": "B019R4QRXA", "name": "Beurer BM 58", "category": "blood_pressure"},

    # ===========================================
    # BEURER TENS/EMS DEVICES (EM Series)
    # ===========================================
    # Priority 1
    {"asin": "B01MTZLOPQ", "name": "Beurer EM 59", "category": "pain_tens"},
    # Priority 2
    {"asin": "B085CXYMFN", "name": "Beurer EM 50", "category": "pain_tens"},
    {"asin": "B0C75H3QH2", "name": "Beurer EM 55", "category": "pain_tens"},
    # Priority 3 (legacy)
    {"asin": "B00OZ9ORQA", "name": "Beurer EM 49", "category": "pain_tens"},

    # ===========================================
    # BEURER INFRARED DEVICES (IL Series)
    # ===========================================
    {"asin": "B001Q3S39K", "name": "Beurer IL 50", "category": "infrarot"},
    {"asin": "B0CHJ1VR6S", "name": "Beurer IL 60", "category": "infrarot"},

    # ===========================================
    # COMPETITORS - Blood Pressure
    # ===========================================
    {"asin": "B0757LSGNX", "name": "Omron M500 Intelli IT", "category": "blood_pressure"},

    # ===========================================
    # COMPETITORS - TENS/EMS
    # ===========================================
    {"asin": "B082B6X8GX", "name": "AUVON TENS Gerät", "category": "pain_tens"},
    {"asin": "B0DKFDKCSP", "name": "Orthomechanik TENS/EMS", "category": "pain_tens"},
    {"asin": "B0DJLQNNZZ", "name": "Comfytemp TENS Gerät", "category": "pain_tens"},
    {"asin": "B0F9W61LCG", "name": "GHTENS", "category": "pain_tens"},

    # ===========================================
    # COMPETITORS - Infrared / Heat
    # ===========================================
    {"asin": "B0BRXKD92T", "name": "Comfytemp Wärmegürtel", "category": "infrarot"},
    {"asin": "B0BQ6ZF5C3", "name": "Slimpal Wärmegürtel", "category": "infrarot"},
    {"asin": "B08QWYTXHL", "name": "Medisana IR 850", "category": "infrarot"},
]


class AmazonCrawler(BaseCrawler):
    """Crawler for Amazon.de reviews using Apify."""

    name = "amazon"
    tool = "apify"

    def __init__(self):
        super().__init__()
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN must be set")
        self.apify = ApifyClient(self.api_token)

    async def _run_actor(self, asin: str, max_reviews: int = 100) -> List[Dict]:
        """Run Apify Actor to scrape Amazon reviews."""
        return await self.apify.run_actor(
            actor_id="junglee~amazon-reviews-scraper",
            input_data={
                "productUrls": [{"url": f"https://www.amazon.de/dp/{asin}"}],
                "maxReviews": max_reviews,
            }
        )

    def _parse_review(self, review: Dict, product_info: Dict) -> Dict[str, Any]:
        """Convert Apify review to social item format."""
        # Apify junglee actor returns: reviewTitle, reviewDescription, ratingScore, date, reviewId, reviewUrl, isVerified
        review_id = review.get("reviewId", "")
        review_url = review.get("reviewUrl") or f"https://www.amazon.de/gp/customer-reviews/{review_id}"

        # Build content from title + description
        title = (review.get("reviewTitle") or "").strip()
        text = (review.get("reviewDescription") or "").strip()
        content = f"{title}\n\n{text}" if title else text

        # Parse date - returns ISO format like "2025-08-19"
        posted_at = review.get("date")

        # Parse helpful votes (reviewReaction is a string like "39")
        helpful_votes = 0
        if review.get("reviewReaction"):
            try:
                helpful_votes = int(review.get("reviewReaction", 0))
            except (ValueError, TypeError):
                pass

        return {
            "source": "amazon.de",
            "source_url": review_url,
            "source_id": review_id,
            "title": title[:500] if title else None,
            "content": content[:2000],
            "author": review.get("userId"),  # No username available, use userId
            "posted_at": parse_to_yyyy_mm_dd(posted_at),
            "crawler_tool": "apify",
            "raw_data": {
                "asin": product_info["asin"],
                "product_name": product_info["name"],
                "category": product_info["category"],
                "rating": review.get("ratingScore"),
                "verified_purchase": review.get("isVerified", False),
                "helpful_votes": helpful_votes,
                "variant": review.get("variant"),
            }
        }

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch reviews from Amazon.de."""
        max_products = config.get("max_products", len(AMAZON_ASINS))
        max_reviews_per_product = config.get("max_reviews", 50)
        products = AMAZON_ASINS[:max_products]

        all_items = []
        for product in products:
            try:
                logger.info(f"[amazon] Fetching reviews for {product['name']} ({product['asin']})")
                reviews = await self._run_actor(product["asin"], max_reviews_per_product)

                for review in reviews:
                    # Skip error responses or reviews with no content
                    if review.get("error"):
                        continue
                    if not review.get("reviewDescription") and not review.get("reviewTitle"):
                        continue

                    item = self._parse_review(review, product)
                    if len(item["content"]) >= 30:  # Skip very short reviews
                        all_items.append(item)

                logger.info(f"[amazon] Found {len(reviews)} reviews for {product['name']}")

                # Rate limit between products
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[amazon] Error fetching {product['name']}: {e}")
                continue

        return all_items


# =============================================================================
# REDDIT CRAWLER (Every 6 hours)
# Uses Reddit's public JSON API directly - no Apify subscription required
# =============================================================================

# Target subreddits for Beurer-relevant health content
# Each subreddit should yield at least 15 relevant posts
REDDIT_TARGET_SUBREDDITS = [
    {
        "name": "ChronicPain",
        "category": "pain_tens",
        "min_posts": 25,
        "collection_type": "brand",
    },
    {
        "name": "backpain",
        "category": "pain_tens",
        "min_posts": 25,
        "collection_type": "brand",
    },
    {
        "name": "bloodpressure",
        "category": "blood_pressure",
        "min_posts": 25,
        "collection_type": "brand",
    },
    {
        "name": "germany",
        "category": "other",
        "min_posts": 25,
        "collection_type": "brand",
        "search_only": True,  # Don't fetch new/hot firehose — too noisy
        # For r/germany, only search for health-related posts
        "search_queries": ["blood pressure", "TENS", "pain", "health"],
    },
    {
        "name": "Gesundheit",
        "category": "other",
        "min_posts": 20,
        "collection_type": "brand",
    },
    # Journey intelligence subreddits (pre-purchase pain awareness)
    {
        "name": "Fibromyalgia",
        "category": "pain_tens",
        "min_posts": 20,
        "collection_type": "journey",
    },
    {
        "name": "Sciatica",
        "category": "pain_tens",
        "min_posts": 20,
        "collection_type": "journey",
    },
    {
        "name": "hypertension",
        "category": "blood_pressure",
        "min_posts": 20,
        "collection_type": "journey",
    },
    {
        "name": "Endo",
        "category": "menstrual",
        "min_posts": 20,
        "collection_type": "journey",
    },
    {
        "name": "PelvicFloor",
        "category": "pain_tens",
        "min_posts": 20,
        "collection_type": "journey",
    },
    {
        "name": "AppleWatchFitness",
        "category": "blood_pressure",
        "min_posts": 15,
        "collection_type": "brand",
        "search_only": True,  # Don't fetch new/hot firehose — too noisy
        "search_queries": ["blood pressure monitor", "Beurer", "health device"],
    },
]

# Health-related search queries for global Reddit search
REDDIT_HEALTH_SEARCHES = [
    "blood pressure monitor",
    "TENS unit pain relief",
    "chronic pain management",
    "back pain treatment",
    "period pain relief",
    # Journey intelligence: broader pain/solution queries
    "nerve pain relief what works",
    "heat therapy vs TENS pain",
    "home pain management without medication",
    "best way to monitor blood pressure at home",
    "pelvic floor pain relief device",
]

# User agent for Reddit API requests
REDDIT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"


class RedditCrawler(BaseCrawler):
    """Crawler for Reddit using direct JSON API (no Apify required)."""

    name = "reddit"
    tool = "reddit_json_api"

    def __init__(self):
        super().__init__()
        # Note: No Apify token required - uses Reddit's public JSON API

    async def _fetch_post_comments(self, permalink: str, limit: int = 5) -> List[Dict]:
        """Fetch top comments for a Reddit post.

        Args:
            permalink: Reddit permalink (e.g. /r/subreddit/comments/id/title/)
            limit: Max number of top-level comments to fetch

        Returns:
            List of comment dicts with content, author, votes, etc.
        """
        url = f"https://www.reddit.com{permalink}.json?limit={limit}&sort=top"
        comments = []

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})

                if resp.status_code == 429:
                    logger.warning(f"[reddit] Rate limited on comments, waiting...")
                    await asyncio.sleep(5)
                    resp = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})

                if resp.status_code != 200:
                    logger.debug(f"[reddit] Comment fetch failed: {resp.status_code}")
                    return []

                data = resp.json()

                # Reddit returns a 2-element array: [post, comments_listing]
                if not isinstance(data, list) or len(data) < 2:
                    return []

                comment_listing = data[1].get("data", {}).get("children", [])

                for child in comment_listing:
                    if child.get("kind") != "t1":
                        continue
                    comment_data = child.get("data", {})
                    body = (comment_data.get("body") or "").strip()
                    if not body or body == "[deleted]" or body == "[removed]":
                        continue

                    comments.append({
                        "content": body[:5000],
                        "author": comment_data.get("author"),
                        "votes": comment_data.get("score", 0),
                        "is_accepted": False,
                        "position": len(comments),
                        "posted_at": parse_to_yyyy_mm_dd(comment_data.get("created_utc")),
                        "source_id": comment_data.get("id"),
                    })

            except Exception as e:
                logger.debug(f"[reddit] Comment fetch exception: {e}")

        return comments

    def _parse_post(self, post: Dict, subreddit: str = "", collection_type: str = "brand") -> Dict[str, Any]:
        """Convert Reddit JSON API post to social item format.

        Reddit JSON API post fields:
        - id: post ID
        - title: post title
        - selftext: post body text
        - author: username
        - subreddit: subreddit name
        - score: upvotes
        - num_comments: comment count
        - permalink: /r/subreddit/comments/id/title/
        - created_utc: Unix timestamp
        """
        title = (post.get("title") or "").strip()
        body = (post.get("selftext") or "").strip()
        content = f"{title}\n\n{body}" if body else title

        # Build full URL from permalink
        permalink = post.get("permalink", "")
        source_url = f"https://www.reddit.com{permalink}" if permalink else None

        # Get subreddit name
        sub = post.get("subreddit") or subreddit

        return {
            "source": "reddit",
            "source_url": source_url,
            "source_id": post.get("id"),
            "title": title[:500] if title else None,
            "content": content[:2000] if content else "",
            "author": post.get("author"),
            "posted_at": parse_to_yyyy_mm_dd(post.get("created_utc")),
            "crawler_tool": "reddit_json_api",
            "collection_type": collection_type,
            "raw_data": {
                "subreddit": sub,
                "score": post.get("score"),
                "num_comments": post.get("num_comments"),
                "upvote_ratio": post.get("upvote_ratio"),
                "is_self": post.get("is_self"),
            }
        }

    async def _fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 25,
        sort: str = "new"
    ) -> List[Dict]:
        """Fetch posts from a subreddit using Reddit's JSON API."""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})

                if resp.status_code == 429:
                    logger.warning(f"[reddit] Rate limited on r/{subreddit}, waiting...")
                    await asyncio.sleep(5)
                    resp = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})

                if resp.status_code != 200:
                    logger.error(f"[reddit] Error fetching r/{subreddit}: {resp.status_code}")
                    return []

                data = resp.json()
                children = data.get("data", {}).get("children", [])
                return [child.get("data", {}) for child in children]

            except Exception as e:
                logger.error(f"[reddit] Exception fetching r/{subreddit}: {e}")
                return []

    async def _search_subreddit(
        self,
        subreddit: str,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search for posts within a specific subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "relevance",
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": REDDIT_USER_AGENT}
                )

                if resp.status_code != 200:
                    logger.error(f"[reddit] Search error in r/{subreddit}: {resp.status_code}")
                    return []

                data = resp.json()
                children = data.get("data", {}).get("children", [])
                return [child.get("data", {}) for child in children]

            except Exception as e:
                logger.error(f"[reddit] Search exception in r/{subreddit}: {e}")
                return []

    async def _global_search(self, query: str, limit: int = 15) -> List[Dict]:
        """Search all of Reddit for posts matching a query."""
        url = "https://www.reddit.com/search.json"
        params = {
            "q": query,
            "sort": "relevance",
            "type": "link",
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": REDDIT_USER_AGENT}
                )

                if resp.status_code != 200:
                    logger.error(f"[reddit] Global search error: {resp.status_code}")
                    return []

                data = resp.json()
                children = data.get("data", {}).get("children", [])
                return [child.get("data", {}) for child in children]

            except Exception as e:
                logger.error(f"[reddit] Global search exception: {e}")
                return []

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch posts from Reddit using direct JSON API.

        Targets: r/ChronicPain, r/backpain, r/bloodpressure, r/germany
        Requirement: At least 15 results from each subreddit.
        """
        all_items = []
        subreddit_counts = {}
        seen_urls = set()  # Deduplication

        def add_item(item):
            """Add item if not a duplicate."""
            if item["source_url"] and item["source_url"] not in seen_urls:
                if item["content"] and len(item["content"]) >= 30:
                    seen_urls.add(item["source_url"])
                    all_items.append(item)
                    return True
            return False

        # Phase 1: Fetch from each target subreddit
        for sub_config in REDDIT_TARGET_SUBREDDITS:
            sub_name = sub_config["name"]
            min_posts = sub_config.get("min_posts", 25)
            search_queries = sub_config.get("search_queries")
            collection_type = sub_config.get("collection_type", "brand")

            subreddit_counts[sub_name] = 0
            search_only = sub_config.get("search_only", False)
            logger.info(f"[reddit] Fetching r/{sub_name} [{collection_type}]{' (search_only)' if search_only else ''}...")

            if not search_only:
                # Fetch newest posts
                posts = await self._fetch_subreddit_posts(sub_name, limit=min_posts, sort="new")

                for post in posts:
                    item = self._parse_post(post, sub_name, collection_type)
                    if add_item(item):
                        subreddit_counts[sub_name] += 1

                logger.info(f"[reddit] r/{sub_name}: got {len(posts)} posts, kept {subreddit_counts[sub_name]}")

                # Also fetch hot posts for variety
                hot_posts = await self._fetch_subreddit_posts(sub_name, limit=15, sort="hot")
                for post in hot_posts:
                    item = self._parse_post(post, sub_name, collection_type)
                    if add_item(item):
                        subreddit_counts[sub_name] += 1

            # If subreddit has specific search queries (e.g., r/germany health topics)
            if search_queries:
                for query in search_queries:
                    logger.info(f"[reddit] Searching r/{sub_name} for: {query}")
                    search_posts = await self._search_subreddit(sub_name, query, limit=10)

                    for post in search_posts:
                        item = self._parse_post(post, sub_name, collection_type)
                        if add_item(item):
                            subreddit_counts[sub_name] += 1

                    await asyncio.sleep(1)  # Rate limiting for searches

            # Rate limiting between subreddits
            await asyncio.sleep(2)

        # Phase 2: Global health-related searches
        for query in REDDIT_HEALTH_SEARCHES:
            logger.info(f"[reddit] Global search: {query}")
            posts = await self._global_search(query, limit=10)

            for post in posts:
                item = self._parse_post(post)
                add_item(item)

            await asyncio.sleep(2)

        # Log final counts
        logger.info(f"[reddit] Subreddit counts: {subreddit_counts}")
        logger.info(f"[reddit] Total unique posts: {len(all_items)}")

        # Verify minimum requirement
        for sub, count in subreddit_counts.items():
            if count < 15:
                logger.warning(f"[reddit] WARNING: r/{sub} has only {count} posts (need 15+)")

        # Phase 3: Fetch top comments for posts
        fetch_comments = config.get("fetch_comments", True)
        max_comments_per_post = config.get("max_comments_per_post", 5)

        if fetch_comments:
            comment_count = 0
            for item in all_items:
                num_comments = (item.get("raw_data") or {}).get("num_comments", 0)
                if not num_comments or num_comments <= 0:
                    continue

                permalink = None
                source_url = item.get("source_url", "")
                if source_url.startswith("https://www.reddit.com"):
                    permalink = source_url.replace("https://www.reddit.com", "")

                if not permalink:
                    continue

                try:
                    comments = await self._fetch_post_comments(
                        permalink, limit=max_comments_per_post
                    )

                    if comments:
                        # Set question content = original post (title + selftext)
                        item["_question_content"] = item["content"]
                        item["_answers"] = comments

                        # Append top 2 comment previews to content for better classification
                        previews = []
                        for c in comments[:2]:
                            preview = c["content"][:200]
                            if len(c["content"]) > 200:
                                preview += "..."
                            previews.append(f"Top comment: {preview}")
                        if previews:
                            item["content"] = item["content"] + "\n\n---\n" + "\n".join(previews)
                            item["content"] = item["content"][:2000]

                        comment_count += 1

                    # Rate limit: 1s between comment fetches
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.debug(f"[reddit] Comment fetch error: {e}")
                    continue

            logger.info(f"[reddit] Fetched comments for {comment_count} posts")

        return all_items


# =============================================================================
# YOUTUBE CRAWLER (Weekly)
# =============================================================================

# YouTube channels/videos to monitor for health content
YOUTUBE_TARGETS = [
    # Existing searches
    {"type": "search", "query": "Blutdruck messen Tipps", "max_videos": 10},
    {"type": "search", "query": "TENS Gerät Anwendung", "max_videos": 10},
    {"type": "search", "query": "Regelschmerzen lindern", "max_videos": 10},
    # New searches from Peec AI data
    {"type": "search", "query": "Blutdruckmessgerät Test 2026", "max_videos": 10},
    {"type": "search", "query": "TENS Gerät Erfahrung", "max_videos": 10},
    {"type": "search", "query": "Beurer Test", "max_videos": 10},
    {"type": "search", "query": "Omron vs Beurer", "max_videos": 10},
    {"type": "search", "query": "TOP 5 Blutdruckmessgeräte", "max_videos": 10},
    {"type": "search", "query": "TENS Rückenschmerzen", "max_videos": 10},
    # Channel monitoring (Peec AI: directly cited by AI)
    {"type": "channel", "channel_url": "https://www.youtube.com/@produktvergleich9438", "max_videos": 10},
]


class YouTubeCrawler(BaseCrawler):
    """Crawler for YouTube transcripts and comments using Apify.

    Uses two Apify actors:
    - streamers~youtube-scraper: Searches YouTube and returns video metadata/URLs + subtitles
    - streamers~youtube-comments-scraper: Scrapes comments from specific video URLs

    Three-step pipeline for "search" targets:
    1. Find videos via search (with subtitle download enabled)
    2. Extract transcripts as `youtube_transcript` items (source per video)
    3. Scrape comments as `youtube` items (source per comment, deduped by comment ID)

    For "channel" targets: Passes channel URL directly to the comments scraper (no transcripts).
    """

    name = "youtube"
    tool = "apify"

    def __init__(self):
        super().__init__()
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN must be set")
        self.apify = ApifyClient(self.api_token)

    def _parse_comment(self, comment: Dict, video_info: Dict) -> Dict[str, Any]:
        """Convert YouTube comment to social item format.

        Handles both old format (nested comments array) and new flat format
        from streamers~youtube-comments-scraper.
        """
        # New actor returns: comment, author, videoId, title, publishedTimeText, voteCount, cid
        content = comment.get("text") or comment.get("comment", "")
        author = comment.get("author", "")
        comment_id = comment.get("id") or comment.get("cid", "")
        posted_at = comment.get("publishedAt") or comment.get("publishedTimeText")

        # Build comment-specific URL for unique dedup (fixes 1-comment-per-video bug)
        video_id = video_info.get("id", "")
        if comment_id and video_id:
            source_url = f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"
        elif comment_id:
            source_url = f"{video_info.get('url', '')}&lc={comment_id}"
        else:
            source_url = video_info.get("url")

        return {
            "source": "youtube",
            "source_url": source_url,
            "source_id": comment_id,
            "title": video_info.get("title", "")[:500],
            "content": content[:2000],
            "author": author,
            "posted_at": parse_to_yyyy_mm_dd(posted_at),
            "crawler_tool": "apify",
            "collection_type": "brand",
            "raw_data": {
                "video_id": video_info.get("id"),
                "video_title": video_info.get("title"),
                "likes": comment.get("likes") or comment.get("voteCount"),
                "reply_count": comment.get("replyCount"),
            }
        }

    def _parse_transcript(self, video: Dict, query: str = "") -> Dict[str, Any] | None:
        """Convert a video with subtitle data into a youtube_transcript social item.

        Args:
            video: Video dict from _search_videos() with subtitles field
            query: Search query that found this video (for raw_data context)

        Returns:
            Social item dict with source='youtube_transcript', or None if no usable subtitle text
        """
        subtitles = video.get("subtitles", "")
        if isinstance(subtitles, list):
            # Actor may return list of subtitle entries or segments
            parts = []
            for seg in subtitles:
                if isinstance(seg, dict):
                    parts.append(seg.get("plaintext") or seg.get("text", ""))
                else:
                    parts.append(str(seg))
            subtitles = " ".join(parts)

        subtitles = (subtitles or "").strip()
        if len(subtitles) < 50:
            return None

        # Truncate to 5000 chars — enough for classification
        content = subtitles[:5000]
        title = video.get("title", "")
        description = (video.get("description") or "")[:500]

        return {
            "source": "youtube_transcript",
            "source_url": video.get("url"),
            "source_id": video.get("id"),
            "title": title[:500] if title else None,
            "content": content,
            "author": video.get("channelName"),
            "posted_at": parse_to_yyyy_mm_dd(video.get("date")),
            "crawler_tool": "apify",
            "collection_type": "brand",
            "raw_data": {
                "video_id": video.get("id"),
                "video_title": title,
                "description_snippet": description,
                "views": video.get("viewCount"),
                "likes": video.get("likes"),
                "duration": video.get("duration"),
                "channel": video.get("channelName"),
                "search_query": query,
                "transcript_length": len(subtitles),
            }
        }

    async def _search_videos(self, query: str, max_videos: int = 10) -> List[Dict]:
        """Search YouTube for videos matching a query.

        Uses streamers~youtube-scraper with a YouTube search results URL.
        Returns list of video dicts with 'url', 'id', 'title' keys.
        """
        from urllib.parse import quote_plus
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"

        results = await self.apify.run_actor(
            actor_id="streamers~youtube-scraper",
            input_data={
                "startUrls": [{"url": search_url}],
                "maxResults": max_videos,
                "downloadSubtitles": True,
                "subtitlesLanguage": "de",
                "subtitlesFormat": "plaintext",
                "preferAutoGeneratedSubtitles": True,
            },
            timeout_minutes=5
        )

        if results:
            logger.info(f"[youtube] Video response keys: {list(results[0].keys())}")

        videos = []
        for r in results:
            if r.get("error") or not r.get("url"):
                continue
            # Extract plaintext subtitles from nested structure
            # Actor returns: subtitles=[{"plaintext": "...", "language": "de", "type": "auto_generated"}]
            raw_subs = r.get("subtitles") or []
            subtitle_text = ""
            if isinstance(raw_subs, list) and raw_subs:
                for sub_entry in raw_subs:
                    if isinstance(sub_entry, dict) and sub_entry.get("plaintext"):
                        subtitle_text = sub_entry["plaintext"]
                        break
            elif isinstance(raw_subs, str):
                subtitle_text = raw_subs

            videos.append({
                "id": r.get("id", ""),
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "description": r.get("text") or r.get("description", ""),
                "date": r.get("date") or r.get("uploadDate") or r.get("publishedAt"),
                "viewCount": r.get("viewCount"),
                "likes": r.get("likes"),
                "duration": r.get("duration"),
                "channelName": r.get("channelName") or r.get("channelTitle"),
                "subtitles": subtitle_text,
            })

        return videos

    async def _scrape_comments(self, video_urls: List[str], max_comments: int = 100) -> List[Dict]:
        """Scrape comments from a list of YouTube video URLs.

        Uses streamers~youtube-comments-scraper with startUrls.
        Returns flat list of comment dicts.
        """
        if not video_urls:
            return []

        start_urls = [{"url": url} for url in video_urls]
        results = await self.apify.run_actor(
            actor_id="streamers~youtube-comments-scraper",
            input_data={
                "startUrls": start_urls,
                "maxResults": max_comments,
            },
            timeout_minutes=10
        )

        return [r for r in results if not r.get("error")]

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch transcripts and comments from YouTube videos.

        Three-step process for "search" targets:
        1. Use youtube-scraper to find videos (with subtitle download)
        2. Extract transcripts as youtube_transcript items
        3. Scrape comments as youtube items (deduped by comment ID)

        For "channel" targets: pass channel URL directly to comments scraper (no transcripts).
        """
        max_comments = config.get("max_comments", 100)

        all_items = []
        for target in YOUTUBE_TARGETS:
            target_type = target.get("type", "search")
            max_videos = target.get("max_videos", 10)

            try:
                if target_type == "channel":
                    channel_url = target["channel_url"]
                    logger.info(f"[youtube] Fetching channel: {channel_url}")
                    comments = await self._scrape_comments([channel_url], max_comments)

                    for comment in comments:
                        video_id = comment.get("videoId", "")
                        video_info = {
                            "id": video_id,
                            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else channel_url,
                            "title": comment.get("title", ""),
                        }
                        item = self._parse_comment(comment, video_info)
                        if len(item["content"]) >= 30:
                            all_items.append(item)

                    logger.info(f"[youtube] Found {len(comments)} comments from channel")

                else:
                    query = target["query"]
                    logger.info(f"[youtube] Step 1: Searching for videos: {query}")

                    # Step 1: Find videos (with subtitles)
                    videos = await self._search_videos(query, max_videos)
                    logger.info(f"[youtube] Found {len(videos)} videos for: {query}")

                    if not videos:
                        continue

                    # Step 1.5: Extract transcripts from videos with subtitles
                    transcript_count = 0
                    for video in videos:
                        transcript_item = self._parse_transcript(video, query)
                        if transcript_item and len(transcript_item["content"]) >= 30:
                            all_items.append(transcript_item)
                            transcript_count += 1
                    if transcript_count:
                        logger.info(f"[youtube] Extracted {transcript_count} transcripts for: {query}")

                    # Step 2: Scrape comments from found videos
                    video_urls = [v["url"] for v in videos]
                    logger.info(f"[youtube] Step 2: Scraping comments from {len(video_urls)} videos")
                    comments = await self._scrape_comments(video_urls, max_comments)

                    # Build video lookup for metadata
                    video_lookup = {v["url"]: v for v in videos}
                    # Also index by video ID
                    for v in videos:
                        if v.get("id"):
                            video_lookup[v["id"]] = v

                    for comment in comments:
                        video_id = comment.get("videoId", "")
                        page_url = comment.get("pageUrl", "")
                        video_info = (
                            video_lookup.get(page_url)
                            or video_lookup.get(video_id)
                            or {
                                "id": video_id,
                                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                                "title": comment.get("title", ""),
                            }
                        )
                        item = self._parse_comment(comment, video_info)
                        if len(item["content"]) >= 30:
                            all_items.append(item)

                    logger.info(f"[youtube] Found {len(comments)} comments for: {query}")

                await asyncio.sleep(2)

            except Exception as e:
                label = target.get("channel_url") or target.get("query", "unknown")
                logger.error(f"[youtube] Error for {label}: {e}")
                continue

        return all_items


# =============================================================================
# TIKTOK CRAWLER (Weekly, Low Priority)
# =============================================================================

class TikTokCrawler(BaseCrawler):
    """Crawler for TikTok using Apify. Low priority - target audience is 50+."""

    name = "tiktok"
    tool = "apify"

    def __init__(self):
        super().__init__()
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN must be set")
        self.apify = ApifyClient(self.api_token)

    def _parse_video(self, video: Dict) -> Dict[str, Any]:
        """Convert TikTok video to social item format."""
        return {
            "source": "tiktok",
            "source_url": video.get("webVideoUrl"),
            "source_id": video.get("id"),
            "title": video.get("desc", "")[:500],
            "content": video.get("desc", "")[:2000],
            "author": video.get("authorMeta", {}).get("name"),
            "posted_at": parse_to_yyyy_mm_dd(video.get("createTime")),
            "crawler_tool": "apify",
            "raw_data": {
                "plays": video.get("playCount"),
                "likes": video.get("diggCount"),
                "comments": video.get("commentCount"),
                "shares": video.get("shareCount"),
                "hashtags": video.get("hashtags", []),
            }
        }

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch videos from TikTok."""
        max_videos = config.get("max_videos", 50)

        search_terms = [
            "Blutdruck",
            "TENS Gerät",
            "Periodenschmerzen",
        ]

        all_items = []
        for term in search_terms:
            try:
                logger.info(f"[tiktok] Searching for: {term}")

                # Use clockworks/tiktok-scraper actor
                results = await self.apify.run_actor(
                    actor_id="clockworks~tiktok-scraper",
                    input_data={
                        "searchQueries": [term],
                        "resultsPerPage": max_videos,
                    },
                    timeout_minutes=10
                )

                for video in results:
                    if video.get("error"):
                        continue

                    item = self._parse_video(video)
                    if len(item["content"]) >= 10:
                        all_items.append(item)

                logger.info(f"[tiktok] Found {len(results)} videos for: {term}")
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[tiktok] Error searching {term}: {e}")
                continue

        return all_items


# =============================================================================
# INSTAGRAM CRAWLER (Weekly, Low Priority)
# =============================================================================

class InstagramCrawler(BaseCrawler):
    """Crawler for Instagram using Apify. Two-step pipeline:
    1. Search posts by hashtag via apify~instagram-scraper
    2. Fetch comments for posts via apify~instagram-comment-scraper
    """

    name = "instagram"
    tool = "apify"

    def __init__(self):
        super().__init__()
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN must be set")
        self.apify = ApifyClient(self.api_token)

    def _parse_post(self, post: Dict) -> Dict[str, Any]:
        """Convert Instagram post to social item format."""
        caption = post.get("caption", "")

        return {
            "source": "instagram",
            "source_url": post.get("url"),
            "source_id": post.get("id"),
            "title": caption[:100] if caption else None,
            "content": caption[:2000] if caption else "",
            "author": post.get("ownerUsername"),
            "posted_at": parse_to_yyyy_mm_dd(post.get("timestamp")),
            "crawler_tool": "apify",
            "raw_data": {
                "likes": post.get("likesCount"),
                "comments": post.get("commentsCount"),
                "type": post.get("type"),
                "hashtags": post.get("hashtags", []),
            }
        }

    async def _fetch_comments_for_posts(
        self, post_urls: List[str], max_comments: int = 20
    ) -> Dict[str, List[Dict]]:
        """Fetch comments for a batch of Instagram post URLs.

        Args:
            post_urls: List of Instagram post URLs to fetch comments for
            max_comments: Max comments per post

        Returns:
            Dict mapping post URL → list of answer dicts
        """
        if not post_urls:
            return {}

        try:
            results = await self.apify.run_actor(
                actor_id="apify~instagram-comment-scraper",
                input_data={
                    "directUrls": post_urls,
                    "resultsPerPost": max_comments,
                },
                timeout_minutes=10,
            )
        except Exception as e:
            logger.error(f"[instagram] Comment scraper failed: {e}")
            return {}

        # Group comments by post URL
        comments_by_url: Dict[str, List[Dict]] = {}
        for comment in results:
            # The actor returns postUrl or inputUrl to identify the parent
            post_url = comment.get("postUrl") or comment.get("inputUrl") or ""
            if not post_url:
                continue

            text = comment.get("text", "")
            if not text or len(text) < 5:
                continue

            answer = {
                "content": text[:2000],
                "author": comment.get("ownerUsername") or comment.get("username", ""),
                "posted_at": parse_to_yyyy_mm_dd(
                    comment.get("timestamp") or comment.get("createdAt")
                ),
                "raw_data": {
                    "likes": comment.get("likesCount") or comment.get("likes", 0),
                    "comment_id": comment.get("id", ""),
                },
            }
            comments_by_url.setdefault(post_url, []).append(answer)

        logger.info(
            f"[instagram] Fetched comments for {len(comments_by_url)}/{len(post_urls)} posts"
        )
        return comments_by_url

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch posts from Instagram, then fetch comments for posts that have them."""
        max_posts = config.get("max_posts", 50)
        fetch_comments = config.get("fetch_comments", True)
        max_comments = config.get("max_comments_per_post", 20)

        hashtags = [
            "blutdruck",
            "tensgerät",
            "periodenschmerzen",
            "beurer",
        ]

        # Phase 1: Fetch posts by hashtag
        all_items = []
        for hashtag in hashtags:
            try:
                logger.info(f"[instagram] Fetching #{hashtag}")

                results = await self.apify.run_actor(
                    actor_id="apify~instagram-scraper",
                    input_data={
                        "hashtags": [hashtag],
                        "resultsLimit": max_posts,
                    },
                    timeout_minutes=10,
                )

                for post in results:
                    if post.get("error"):
                        continue

                    item = self._parse_post(post)
                    if len(item["content"]) >= 10:
                        all_items.append(item)

                logger.info(f"[instagram] Found {len(results)} posts for #{hashtag}")
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[instagram] Error fetching #{hashtag}: {e}")
                continue

        # Phase 2: Fetch comments for posts that have them
        if fetch_comments:
            posts_with_comments = [
                item for item in all_items
                if (item.get("raw_data") or {}).get("comments", 0) > 0
                and item.get("source_url")
            ]

            if posts_with_comments:
                post_urls = [item["source_url"] for item in posts_with_comments]
                logger.info(f"[instagram] Fetching comments for {len(post_urls)} posts")

                comments_by_url = await self._fetch_comments_for_posts(
                    post_urls, max_comments=max_comments
                )

                comment_count = 0
                for item in posts_with_comments:
                    answers = comments_by_url.get(item["source_url"], [])
                    if not answers:
                        continue

                    item["_question_content"] = item["content"]
                    item["_answers"] = answers

                    # Append top 2 comment previews to content for classification
                    previews = []
                    for a in answers[:2]:
                        preview = a["content"][:200]
                        if len(a["content"]) > 200:
                            preview += "..."
                        previews.append(f"Top comment: {preview}")
                    if previews:
                        item["content"] = item["content"] + "\n\n---\n" + "\n".join(previews)
                        item["content"] = item["content"][:2000]

                    comment_count += 1

                logger.info(f"[instagram] Attached comments to {comment_count} posts")

        return all_items


# =============================================================================
# TWITTER/X CRAWLER (Weekly)
# =============================================================================

TWITTER_SEARCH_TERMS = [
    # Brand mentions
    "Beurer Blutdruckmessgerät",
    "Beurer TENS",
    "Beurer Infrarot",
    "Beurer BM 27",
    "Beurer EM 59",
    "Omron Blutdruckmessgerät",
    "AUVON TENS",
    # Journey / health topics
    "Blutdruckmessgerät Erfahrung",
    "TENS Gerät Schmerzen",
    "Blutdruck messen zu Hause",
    "Rückenschmerzen Therapie",
    "Periodenschmerzen Hilfe",
]


class TwitterCrawler(BaseCrawler):
    """Crawler for Twitter/X using Apify's tweet-scraper.

    Searches German-language tweets for brand mentions and health device topics.
    """

    name = "twitter"
    tool = "apify"

    def __init__(self):
        super().__init__()
        self.api_token = os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN must be set")
        self.apify = ApifyClient(self.api_token)

    def _parse_tweet(self, tweet: Dict) -> Dict[str, Any] | None:
        """Convert a tweet to social item format.

        Handles field name variants across different actor versions.
        Returns None if the tweet lacks required fields.
        """
        # Content: try text, full_text, tweetText
        content = (
            tweet.get("text")
            or tweet.get("full_text")
            or tweet.get("tweetText")
            or ""
        )
        if len(content) < 10:
            return None

        # Author info
        user = tweet.get("user") or tweet.get("author") or {}
        screen_name = (
            user.get("screen_name")
            or user.get("userName")
            or tweet.get("screen_name")
            or tweet.get("userName")
            or ""
        )

        # Tweet ID and URL
        tweet_id = tweet.get("id") or tweet.get("id_str") or tweet.get("tweetId") or ""
        if screen_name and tweet_id:
            source_url = f"https://x.com/{screen_name}/status/{tweet_id}"
        elif tweet.get("url") or tweet.get("tweetUrl"):
            source_url = tweet.get("url") or tweet.get("tweetUrl")
        else:
            return None

        # Date
        posted_at = (
            tweet.get("created_at")
            or tweet.get("createdAt")
            or tweet.get("timestamp")
        )

        # Engagement metrics (handle variants)
        likes = (
            tweet.get("favorite_count")
            or tweet.get("likeCount")
            or tweet.get("likes")
            or 0
        )
        retweets = (
            tweet.get("retweet_count")
            or tweet.get("retweetCount")
            or tweet.get("retweets")
            or 0
        )
        replies = (
            tweet.get("reply_count")
            or tweet.get("replyCount")
            or tweet.get("replies")
            or 0
        )

        return {
            "source": "twitter",
            "source_url": source_url,
            "source_id": str(tweet_id),
            "title": content[:100],
            "content": content[:2000],
            "author": screen_name,
            "posted_at": parse_to_yyyy_mm_dd(posted_at),
            "crawler_tool": "apify",
            "raw_data": {
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "lang": tweet.get("lang"),
                "hashtags": tweet.get("hashtags") or tweet.get("entities", {}).get("hashtags", []),
            },
        }

    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch tweets matching health device search terms."""
        max_tweets = config.get("max_tweets", 100)
        per_term = max(max_tweets // len(TWITTER_SEARCH_TERMS), 5)

        all_items: List[Dict] = []
        seen_urls: set = set()

        for term in TWITTER_SEARCH_TERMS:
            try:
                logger.info(f"[twitter] Searching: {term}")

                results = await self.apify.run_actor(
                    actor_id="apidojo~tweet-scraper",
                    input_data={
                        "searchTerms": [term],
                        "maxItems": per_term,
                        "sort": "Latest",
                    },
                    timeout_minutes=10,
                )

                added = 0
                for tweet in results:
                    item = self._parse_tweet(tweet)
                    if not item:
                        continue
                    if item["source_url"] in seen_urls:
                        continue
                    seen_urls.add(item["source_url"])
                    all_items.append(item)
                    added += 1

                logger.info(f"[twitter] '{term}': {len(results)} results, {added} new")
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[twitter] Error searching '{term}': {e}")
                continue

        logger.info(f"[twitter] Total unique tweets: {len(all_items)}")
        return all_items
