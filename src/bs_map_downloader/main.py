"""Beat Saber ranked map scraper — CLI entry point."""

import argparse
import asyncio

import httpx

from bs_map_downloader import console
from bs_map_downloader.downloader import download_all
from bs_map_downloader.models import MapInfo
from bs_map_downloader.sources import fetch_beatleader, fetch_mapper, fetch_scoresaber


async def main():
    parser = argparse.ArgumentParser(description="Download ranked Beat Saber maps")
    parser.add_argument("--limit", type=int, default=None, help="Max number of maps to download (per source)")
    parser.add_argument(
        "--source",
        choices=["scoresaber", "beatleader", "both"],
        default="both",
        help="Which leaderboard to fetch from (default: both)",
    )
    parser.add_argument("--mapper", type=str, help="Download all maps by a specific mapper from BeatSaver")
    args = parser.parse_args()

    all_maps: list[MapInfo] = []
    async with httpx.AsyncClient(timeout=30) as client:
        if args.mapper:
            all_maps.extend(await fetch_mapper(client, args.mapper, args.limit))
        else:
            if args.source in ("scoresaber", "both"):
                all_maps.extend(await fetch_scoresaber(client, args.limit))
            if args.source in ("beatleader", "both"):
                all_maps.extend(await fetch_beatleader(client, args.limit))

    # Deduplicate by song hash, keeping first occurrence
    seen: set[str] = set()
    maps: list[MapInfo] = []
    for m in all_maps:
        if m.song_hash not in seen:
            seen.add(m.song_hash)
            maps.append(m)

    if len(maps) < len(all_maps):
        console.print(f"[dim]{len(all_maps) - len(maps)} duplicates across sources removed.[/dim]")

    if not maps:
        console.print("[yellow]No maps found.[/yellow]")
        return

    console.print(f"[bold]{len(maps)} unique maps total.[/bold]")
    await download_all(maps)


def cli():
    asyncio.run(main())


if __name__ == "__main__":
    cli()
