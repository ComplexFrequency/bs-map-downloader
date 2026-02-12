"""Typed data model for scraped Beat Saber maps."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Source(str, Enum):
    SCORESABER = "scoresaber"
    BEATLEADER = "beatleader"
    BEATSAVER = "beatsaver"


CUTOFF_DATE = datetime(2022, 1, 1, tzinfo=timezone.utc)
CUTOFF_TIMESTAMP = int(CUTOFF_DATE.timestamp())


@dataclass
class MapInfo:
    song_hash: str
    song_name: str
    song_author: str
    mapper: str
    ranked_date: str
    source: Source
    stars: float = 0.0
    download_url: str | None = None

    def to_metadata(self) -> dict:
        """Serialize to the camelCase dict format used in metadata.json."""
        return {
            "songHash": self.song_hash,
            "songName": self.song_name,
            "songAuthorName": self.song_author,
            "levelAuthorName": self.mapper,
            "stars": self.stars,
            "rankedDate": self.ranked_date,
            "source": self.source.value,
        }
