"""Base crawler class."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from db.client import get_beurer_supabase, save_social_item, create_crawler_run, update_crawler_run, save_answers, update_item_qa_metadata
from utils.dates import get_weekly_date_range, is_date_in_range

logger = logging.getLogger(__name__)


def _is_health_relevant(item: dict) -> bool:
    """Check if an item's title+content contains at least one health-relevance keyword.

    Used as a pre-save noise filter to prevent irrelevant posts from entering the DB.
    """
    from report.constants import HEALTH_RELEVANCE_KEYWORDS

    title = (item.get("title") or "").lower()
    content = (item.get("content") or "").lower()
    combined = title + " " + content

    return any(kw in combined for kw in HEALTH_RELEVANCE_KEYWORDS)


class BaseCrawler(ABC):
    """Abstract base crawler with save/dedup logic."""

    name: str = "base"
    tool: str = "unknown"

    def __init__(self):
        self.client = get_beurer_supabase()
        self.run_id: str = None
        self.items_crawled: int = 0
        self.items_new: int = 0
        self.items_filtered: int = 0  # Items filtered out by date range
        self.items_health_filtered: int = 0  # Items filtered out by health relevance

    @abstractmethod
    async def fetch_items(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch items from source. Override in subclass."""
        pass

    def _get_date_range(self, config: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Resolve date range from config.

        Handles weekly_mode flag and explicit date_from/date_to parameters.

        Args:
            config: Crawler config dict with optional keys:
                - weekly_mode: If True, sets date_from to 7 days ago
                - date_from: Explicit start date (YYYY-MM-DD)
                - date_to: Explicit end date (YYYY-MM-DD)

        Returns:
            Tuple of (date_from, date_to) or (None, None) if no filtering
        """
        weekly_mode = config.get("weekly_mode", False)
        date_from = config.get("date_from")
        date_to = config.get("date_to")

        # weekly_mode takes precedence if no explicit dates provided
        if weekly_mode and not date_from:
            date_from, date_to = get_weekly_date_range()
            logger.info(f"[{self.name}] Weekly mode: filtering {date_from} to {date_to}")

        return (date_from, date_to)

    def _filter_items_by_date(
        self,
        items: List[Dict[str, Any]],
        date_from: Optional[str],
        date_to: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Filter items by date range.

        Args:
            items: List of crawled items with 'posted_at' field
            date_from: Start date (inclusive), None means no lower bound
            date_to: End date (inclusive), None means no upper bound

        Returns:
            Filtered list of items within date range
        """
        if not date_from and not date_to:
            return items  # No filtering

        filtered = []
        for item in items:
            posted_at = item.get("posted_at")
            if is_date_in_range(posted_at, date_from, date_to):
                filtered.append(item)

        excluded = len(items) - len(filtered)
        if excluded > 0:
            logger.info(f"[{self.name}] Date filter excluded {excluded} items outside {date_from} to {date_to}")

        return filtered

    async def run(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the crawler."""
        config = config or {}

        # Create run record
        run = create_crawler_run(self.client, self.name, self.tool, config)
        self.run_id = run["id"]
        logger.info(f"[{self.name}] Started run {self.run_id}")

        try:
            # Get date range for filtering
            date_from, date_to = self._get_date_range(config)

            items = await self.fetch_items(config)
            items_fetched = len(items)

            # Apply date filtering
            items = self._filter_items_by_date(items, date_from, date_to)
            self.items_filtered = items_fetched - len(items)
            self.items_crawled = len(items)

            for item in items:
                if not _is_health_relevant(item):
                    self.items_health_filtered += 1
                    continue
                answers = item.pop("_answers", [])
                question_content = item.pop("_question_content", None)
                saved = save_social_item(self.client, item, run_id=self.run_id)
                if saved:
                    self.items_new += 1
                    if saved.get("id") and (answers or question_content):
                        count = save_answers(self.client, saved["id"], answers) if answers else 0
                        update_item_qa_metadata(self.client, saved["id"], question_content, count)

            update_crawler_run(
                self.client,
                self.run_id,
                status="success",
                finished_at=datetime.utcnow().isoformat(),
                items_crawled=self.items_crawled,
                items_new=self.items_new
            )

            log_msg = f"[{self.name}] Completed: {items_fetched} fetched"
            if self.items_filtered > 0:
                log_msg += f", {self.items_filtered} filtered by date"
            if self.items_health_filtered > 0:
                log_msg += f", {self.items_health_filtered} filtered by health relevance"
            log_msg += f", {self.items_crawled} in range, {self.items_new} new"
            logger.info(log_msg)

            return {
                "run_id": self.run_id,
                "items_crawled": self.items_crawled,
                "items_new": self.items_new,
                "items_filtered": self.items_filtered,
                "items_health_filtered": self.items_health_filtered
            }

        except Exception as e:
            logger.error(f"[{self.name}] Failed: {e}")
            update_crawler_run(
                self.client,
                self.run_id,
                status="failed",
                finished_at=datetime.utcnow().isoformat(),
                error_message=str(e)
            )
            raise
