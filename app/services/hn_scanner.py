import asyncio
import logging
import re
from typing import List, Dict, Optional
import httpx

from app.services.alert_store import alert_store

logger = logging.getLogger(__name__)

# Only technologies present on the user's RHEL 10 server & K8s cluster
SERVER_TECH_WHITELIST = [
    r"\blinux\b",
    r"\bkernel\b",
    r"\brhel\b",
    r"\bred\s*hat\b",
    r"\bkubernetes\b",
    r"\bk8s\b",
    r"\bcri-o\b",
    r"\bcrio\b",
    r"\benvoy\b",
    r"\bopenssl\b",
    r"\bopenssh\b",
    r"\bsystemd\b",
    r"\bglibc\b",
    r"\bwireguard\b",
    r"\bsudo\b",
    r"\bcontainerd\b",
    r"\blonghorn\b",
    r"\bpihole\b",
    r"\bkafka\b",
    r"\bpostgresql?\b",
]

# Explicit exclusions for technologies NOT on the server to prevent noise
BLACKLIST_EXCLUSIONS = [
    r"\bsynology\b",
    r"\bqnap\b",
    r"\bwindows\b",
    r"\bmacos\b",
    r"\bios\b",
    r"\bandroid\b",
    r"\bcisco\b",
    r"\bfortinet\b",
    r"\bivanti\b",
    r"\bpalo\s*alto\b",
    r"\bwordpress\b",
    r"\bphp\b",
    r"\bexchange\b",
    r"\boutlook\b",
    r"\bzoom\b",
    r"\bteams\b",
    r"\bchrome\b",
    r"\bfirefox\b",
    r"\bsafari\b",
    r"\bvmware\b",
    r"\besxi\b",
]

SECURITY_TRIGGER_WORDS = [
    r"\bcve\b",
    r"\bvulnerab\w+",
    r"\bexploit\w*",
    r"\b0-day\b",
    r"\bzero-day\b",
    r"\bbuffer\s*overflow\b",
    r"\bprivilege\s*escalat\w+",
    r"\bremote\s*code\s*execut\w+",
    r"\brce\b",
    r"\bsecurity\s*advisory\b",
    r"\bbackdoor\b",
]


class HNScanner:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, min_score: int = 40):
        self.min_score = min_score

    def is_relevant(self, title: str) -> bool:
        title_lower = title.lower()

        # 1. Must NOT match any blacklist term
        for bl in BLACKLIST_EXCLUSIONS:
            if re.search(bl, title_lower):
                return False

        # 2. Must match at least one technology from the server whitelist
        tech_match = any(re.search(wl, title_lower) for wl in SERVER_TECH_WHITELIST)
        if not tech_match:
            return False

        # 3. Must match a vulnerability / security trigger term
        sec_match = any(re.search(st, title_lower) for st in SECURITY_TRIGGER_WORDS)
        return sec_match

    async def fetch_security_stories(self) -> List[Dict]:
        """
        Fetches top stories from HN, strictly filtering for user's Linux & K8s stack,
        and deduplicating with persistent alert store.
        """
        matched_stories: List[Dict] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                top_res = await client.get(f"{self.BASE_URL}/topstories.json")
                if top_res.status_code != 200:
                    logger.error(f"Failed to fetch HN topstories: {top_res.status_code}")
                    return []

                story_ids = top_res.json()[:60]

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

                    story_id = f"hn_{item.get('id')}"
                    if alert_store.is_seen(story_id):
                        continue

                    title = item.get("title", "")
                    score = item.get("score", 0)

                    if score >= self.min_score and self.is_relevant(title):
                        url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
                        hn_url = f"https://news.ycombinator.com/item?id={item.get('id')}"
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
            logger.exception(f"Error scanning Hacker News: {e}")

        return matched_stories

    def mark_as_seen(self, story_id: str):
        alert_store.mark_seen(story_id)
