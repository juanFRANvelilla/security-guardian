import json
import os
import logging
from typing import Set

logger = logging.getLogger(__name__)

DATA_FILE = os.getenv("ALERT_STORE_PATH", "data/seen_alerts.json")


class AlertStore:
    def __init__(self, filepath: str = DATA_FILE):
        self.filepath = filepath
        self.seen_ids: Set[str] = set()
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.seen_ids = set(data.get("seen_ids", []))
                    logger.info(f"Loaded {len(self.seen_ids)} seen alert IDs from {self.filepath}")
            except Exception as e:
                logger.error(f"Error loading {self.filepath}: {e}")
                self.seen_ids = set()
        else:
            self.seen_ids = set()

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"seen_ids": list(self.seen_ids)}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {self.filepath}: {e}")

    def is_seen(self, alert_id: str) -> bool:
        return alert_id in self.seen_ids

    def mark_seen(self, alert_id: str):
        self.seen_ids.add(alert_id)
        self.save()


alert_store = AlertStore()
