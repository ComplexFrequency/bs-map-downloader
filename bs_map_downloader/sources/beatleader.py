"""BeatLeader leaderboard API fetcher."""

import asyncio
from datetime import datetime, timezone

import httpx

from bs_map_downloader import console, fetch_progress
from bs_map_downloader.models import CUTOFF_TIMESTAMP, MapInfo, Source

BEATLEADER_API = "https://api.beatleader.xyz/leaderboards"


async def fetch_beatleader(client: httpx.AsyncClient, limit: int | None) -> list[MapInfo]:
    """Paginate BeatLeader leaderboards API and collect unique maps ranked from 2022 onwards."""
    seen_hashes: set[str] = set()
    maps: list[MapInfo] = []
    page = 1
    count = 100

    with fetch_progress(
        "Fetching BeatLeader leaderboards...",
        page="page {task.fields[page]}",
        unique="· {task.fields[unique]} unique maps",
    ) as progress:
        task = progress.add_task("fetch", total=None, page=0, unique=0)

        while True:
            if limit and len(maps) >= limit:
                maps = maps[:limit]
                break

            progress.update(task, page=page, unique=len(maps))

            resp = await client.get(
                BEATLEADER_API,
                params={
                    "type": "ranked",
                    "sortBy": "timestamp",
                    "order": "desc",
                    "page": page,
                    "count": count,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            entries = data.get("data", [])
            if not entries:
                break

            stop = False
            for entry in entries:
                ranked_time = entry.get("difficulty", {}).get("rankedTime", 0)
                if ranked_time < CUTOFF_TIMESTAMP:
                    stop = True
                    break

                song = entry.get("song", {})
                song_hash = song.get("hash", "").lower()
                if not song_hash or song_hash in seen_hashes:
                    continue
                seen_hashes.add(song_hash)

                ranked_dt = datetime.fromtimestamp(ranked_time, tz=timezone.utc)
                maps.append(
                    MapInfo(
                        song_hash=song_hash,
                        song_name=song.get("name", ""),
                        song_author=song.get("author", ""),
                        mapper=song.get("mapper", ""),
                        stars=entry.get("difficulty", {}).get("stars", 0),
                        ranked_date=ranked_dt.isoformat(),
                        source=Source.BEATLEADER,
                    )
                )

                if limit and len(maps) >= limit:
                    break

            if stop:
                break

            page += 1
            await asyncio.sleep(0.15)

    console.print(f"[green]BeatLeader: found {len(maps)} unique maps ranked since 2022.[/green]")
    return maps
