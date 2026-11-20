import asyncio
import logging
from typing import List, Dict, Optional, Set
import httpx

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "cve",
    "vulnerability",
    "exploit",
    "0-day",
    "zero-day",
    "linux",
    "kernel",
    "openssl",
    "openssh",
    "kubernetes",
    "k8s",
    "crio",
    "envoy",
    "rhel",
    "security advisory",
]


class HNScanner:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, min_score: int = 40):
        self.min_score = min_score
        self.seen_story_ids: Set[str] = set()

    async def fetch_security_stories(self, keywords: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetches top & new stories from official HN Firebase API concurrently,
        filtering by security keywords and minimum score.
        """
        kw = [k.lower() for k in (keywords or DEFAULT_KEYWORDS)]
        matched_stories: List[Dict] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch top and best story IDs
                top_res = await client.get(f"{self.BASE_URL}/topstories.json")
                if top_res.status_code != 200:
                    logger.error(f"Failed to fetch HN topstories: {top_res.status_code}")
                    return []

                story_ids = top_res.json()[:60]  # top 60 stories

                async def get_story(sid: int):
                    try:
                        r = await client.get(f"{self.BASE_URL}/item/{sid}.json")
                        return r.json() if r.status_code == 200 else None
                    except Exception:
                        return None

                items = await asyncio.gather(*[get_story(sid) for sid in story_ids])

                for item in items:
                    if not item or item.get("type") != "story":
                        continue

                    story_id = str(item.get("id"))
                    if story_id in self.seen_story_ids:
                        continue

                    title = item.get("title", "")
                    score = item.get("score", 0)
                    title_lower = title.lower()

                    # Match keyword and score
                    has_keyword = any(k in title_lower for k in kw)
                    if has_keyword and score >= self.min_score:
                        url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                        hn_url = f"https://news.ycombinator.com/item?id={story_id}"
                        matched_stories.append({
                            "id": story_id,
                            "title": title,
                            "points": score,
                            "url": url,
                            "hn_url": hn_url,
                            "num_comments": item.get("descendants", 0),
                            "created_at": item.get("time")
                        })

        except Exception as e:
            logger.exception(f"Error scanning Hacker News via Firebase: {e}")

        return matched_stories

    def mark_as_seen(self, story_id: str):
        self.seen_story_ids.add(story_id)
