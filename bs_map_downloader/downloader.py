"""Map download logic with concurrency control."""

import asyncio
import zipfile
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from bs_map_downloader import console
from bs_map_downloader.models import MapInfo

BEATSAVER_MAP_API = "https://api.beatsaver.com/maps/hash"
DOWNLOADS_DIR = Path.cwd() / "downloads"


async def download_map(
    client: httpx.AsyncClient,
    map_info: MapInfo,
    dest: Path,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Look up map on BeatSaver and download the zip. Returns True on success."""
    async with semaphore:
        await asyncio.sleep(0.1)
        try:
            download_url = map_info.download_url
            if not download_url:
                meta_resp = await client.get(f"{BEATSAVER_MAP_API}/{map_info.song_hash}")
                if meta_resp.status_code == 404:
                    console.print(f"[yellow]Not found on BeatSaver: {map_info.song_hash}[/yellow]")
                    return False
                meta_resp.raise_for_status()
                map_data = meta_resp.json()
                download_url = map_data["versions"][0]["downloadURL"]

            dl_resp = await client.get(download_url, follow_redirects=True)
            dl_resp.raise_for_status()
            dest.write_bytes(dl_resp.content)
            return True
        except (httpx.HTTPError, KeyError, IndexError) as e:
            console.print(f"[red]Failed {map_info.song_hash}: {e}[/red]")
            return False


async def download_all(maps: list[MapInfo]) -> list[MapInfo]:
    """Download all maps with a progress bar and concurrency limit.

    Returns the list of successfully downloaded/existing maps.
    """
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    pending: list[MapInfo] = []
    existing: list[MapInfo] = []
    for m in maps:
        dest = DOWNLOADS_DIR / f"{m.song_hash}.zip"
        if dest.exists() and dest.stat().st_size > 0:
            existing.append(m)
        else:
            pending.append(m)

    if existing:
        console.print(f"[dim]Skipping {len(existing)} already-downloaded maps.[/dim]")

    successful = list(existing)

    if not pending:
        console.print("[green]All maps already downloaded, nothing to do.[/green]")
    else:
        semaphore = asyncio.Semaphore(5)
        results: dict[str, bool] = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Downloading maps"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("·"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("download", total=len(pending))

            async with httpx.AsyncClient(timeout=60) as client:
                async def _download(map_info: MapInfo):
                    dest = DOWNLOADS_DIR / f"{map_info.song_hash}.zip"
                    success = await download_map(client, map_info, dest, semaphore)
                    results[map_info.song_hash] = success
                    progress.advance(task)

                await asyncio.gather(*[_download(m) for m in pending])

        newly = sum(1 for v in results.values() if v)
        failed = len(pending) - newly
        console.print(f"[green]Downloaded {newly} new maps ({failed} failed).[/green]")

        successful.extend(m for m in pending if results.get(m.song_hash, False))

    return successful


def install_maps(maps: list[MapInfo], downloads_dir: Path, install_dir: Path) -> None:
    """Extract downloaded zips into install_dir/{song_hash}/, skipping already-extracted."""
    install_dir.mkdir(parents=True, exist_ok=True)
    installed = 0
    skipped = 0

    for m in maps:
        dest = install_dir / m.song_hash
        if dest.exists():
            skipped += 1
            continue

        zip_path = downloads_dir / f"{m.song_hash}.zip"
        if not zip_path.exists():
            continue

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
        installed += 1

    console.print(f"[green]Installed {installed} maps to {install_dir} ({skipped} already present).[/green]")
