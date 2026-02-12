"""Beat Saber ranked map scraper — CLI entry point."""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import httpx

from bs_map_downloader import console
from bs_map_downloader.downloader import DOWNLOADS_DIR, download_all, install_maps
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
    parser.add_argument(
        "--since",
        type=str,
        default="2022-01-01",
        help="Only include maps ranked on or after this date, YYYY-MM-DD (default: 2022-01-01)",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        help="Only include maps ranked on or before this date, YYYY-MM-DD",
    )
    parser.add_argument(
        "--install-dir",
        type=str,
        default=None,
        help="Extract downloaded zips into this directory (e.g. Beat Saber CustomLevels path)",
    )
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    until = datetime.strptime(args.until, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.until else None

    all_maps: list[MapInfo] = []
    async with httpx.AsyncClient(timeout=30) as client:
        if args.mapper:
            all_maps.extend(await fetch_mapper(client, args.mapper, args.limit))
        else:
            if args.source in ("scoresaber", "both"):
                all_maps.extend(await fetch_scoresaber(client, args.limit, since=since, until=until))
            if args.source in ("beatleader", "both"):
                all_maps.extend(await fetch_beatleader(client, args.limit, since=since, until=until))

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
    successful = await download_all(maps)

    if args.install_dir:
        install_maps(successful, DOWNLOADS_DIR, Path(args.install_dir))


def cli():
    asyncio.run(main())


if __name__ == "__main__":
    cli()
