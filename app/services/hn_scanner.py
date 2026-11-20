import logging
from typing import List, Dict, Optional, Set
import httpx

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "vulnerability",
    "cve",
    "exploit",
    "0-day",
    "zero-day",
    "linux kernel",
    "rhel",
    "crio",
    "kubernetes",
    "openssh",
]


class HNScanner:
    BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"

    def __init__(self, min_score: int = 40):
        self.min_score = min_score
        self.seen_story_ids: Set[str] = set()

    async def fetch_security_stories(self, keywords: Optional[List[str]] = None) -> List[Dict]:
        """
        Queries Hacker News (via Algolia API) for recent stories matching security keywords
        with at least `min_score` points.
        """
        kw = keywords or DEFAULT_KEYWORDS
        query = " OR ".join(kw)

        params = {
            "tags": "story",
            "query": query,
            "numericFilters": f"points>={self.min_score}",
            "hitsPerPage": 15,
        }

        stories = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self.BASE_URL, params=params)
                if res.status_code != 200:
                    logger.error(f"HN API returned {res.status_code}")
                    return []

                data = res.json()
                hits = data.get("hits", [])

                for item in hits:
                    story_id = str(item.get("objectID"))
                    if story_id in self.seen_story_ids:
                        continue

                    title = item.get("title", "Sin título")
                    points = item.get("points", 0)
                    url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                    hn_url = f"https://news.ycombinator.com/item?id={story_id}"
                    num_comments = item.get("num_comments", 0)

                    stories.append({
                        "id": story_id,
                        "title": title,
                        "points": points,
                        "url": url,
                        "hn_url": hn_url,
                        "num_comments": num_comments,
                        "created_at": item.get("created_at")
                    })

        except Exception as e:
            logger.exception(f"Error fetching stories from HN: {e}")

        return stories

    def mark_as_seen(self, story_id: str):
        self.seen_story_ids.add(story_id)
