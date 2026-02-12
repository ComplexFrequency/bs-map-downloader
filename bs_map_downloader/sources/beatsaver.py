"""BeatSaver search API fetcher (mapper search)."""

import asyncio

import httpx

from bs_map_downloader import console, fetch_progress
from bs_map_downloader.models import MapInfo, Source

BEATSAVER_SEARCH_API = "https://api.beatsaver.com/search/text"


async def fetch_mapper(client: httpx.AsyncClient, mapper: str, limit: int | None) -> list[MapInfo]:
    """Fetch all maps by a specific mapper from BeatSaver."""
    maps: list[MapInfo] = []
    page = 0

    with fetch_progress(
        f"Fetching maps by {mapper}...",
        page="page {task.fields[page]}",
        count="· {task.fields[count]} maps",
    ) as progress:
        task = progress.add_task("fetch", total=None, page=0, count=0)

        while True:
            if limit and len(maps) >= limit:
                maps = maps[:limit]
                break

            progress.update(task, page=page, count=len(maps))

            resp = await client.get(
                f"{BEATSAVER_SEARCH_API}/{page}",
                params={"q": f"mapper:{mapper}", "sortOrder": "Latest"},
            )
            resp.raise_for_status()
            data = resp.json()

            docs = data.get("docs", [])
            if not docs:
                break

            for entry in docs:
                versions = entry.get("versions", [])
                if not versions:
                    continue

                song_hash = versions[0].get("hash", "").lower()
                if not song_hash:
                    continue

                metadata = entry.get("metadata", {})
                maps.append(
                    MapInfo(
                        song_hash=song_hash,
                        song_name=metadata.get("songName", ""),
                        song_author=metadata.get("songAuthorName", ""),
                        mapper=metadata.get("levelAuthorName", ""),
                        ranked_date=entry.get("uploaded", ""),
                        source=Source.BEATSAVER,
                        download_url=versions[0]["downloadURL"],
                    )
                )

                if limit and len(maps) >= limit:
                    break

            page += 1
            await asyncio.sleep(0.15)

    console.print(f"[green]BeatSaver: found {len(maps)} maps by {mapper}.[/green]")
    return maps
