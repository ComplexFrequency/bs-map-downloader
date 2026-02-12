"""ScoreSaber leaderboard API fetcher."""

import asyncio
from datetime import datetime

import httpx

from bs_map_downloader import console, fetch_progress
from bs_map_downloader.models import CUTOFF_DATE, MapInfo, Source

SCORESABER_API = "https://scoresaber.com/api/leaderboards"


async def fetch_scoresaber(client: httpx.AsyncClient, limit: int | None) -> list[MapInfo]:
    """Paginate ScoreSaber leaderboards API and collect unique maps ranked from 2022 onwards."""
    seen_hashes: set[str] = set()
    maps: list[MapInfo] = []
    page = 1

    with fetch_progress(
        "Fetching ScoreSaber leaderboards...",
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
                SCORESABER_API,
                params={"ranked": "true", "sort": 0, "category": 1, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()

            leaderboards = data.get("leaderboards", [])
            if not leaderboards:
                break

            stop = False
            for entry in leaderboards:
                ranked_date = datetime.fromisoformat(entry["rankedDate"].replace("Z", "+00:00"))
                if ranked_date < CUTOFF_DATE:
                    stop = True
                    break

                song_hash = entry["songHash"].lower()
                if song_hash in seen_hashes:
                    continue
                seen_hashes.add(song_hash)

                maps.append(
                    MapInfo(
                        song_hash=song_hash,
                        song_name=entry.get("songName", ""),
                        song_author=entry.get("songAuthorName", ""),
                        mapper=entry.get("levelAuthorName", ""),
                        stars=entry.get("stars", 0),
                        ranked_date=entry["rankedDate"],
                        source=Source.SCORESABER,
                    )
                )

                if limit and len(maps) >= limit:
                    break

            if stop:
                break

            page += 1
            await asyncio.sleep(0.15)

    console.print(f"[green]ScoreSaber: found {len(maps)} unique maps ranked since 2022.[/green]")
    return maps
