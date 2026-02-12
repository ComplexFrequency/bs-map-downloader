"""Tests for BeatLeader fetcher."""

import pytest
import httpx

from bs_map_downloader.models import CUTOFF_TIMESTAMP, Source
from bs_map_downloader.sources.beatleader import fetch_beatleader


def _bl_entry(song_hash: str, ranked_time: int, stars: float = 4.0) -> dict:
    return {
        "song": {
            "hash": song_hash,
            "name": f"Song {song_hash}",
            "author": "Author",
            "mapper": "Mapper",
        },
        "difficulty": {
            "rankedTime": ranked_time,
            "stars": stars,
        },
    }


# Timestamps for convenience
TS_2023 = 1672531200  # 2023-01-01 UTC
TS_2021 = 1609459200  # 2021-01-01 UTC


def _make_client(pages: dict[int, list[dict]]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        entries = pages.get(page, [])
        return httpx.Response(200, json={"data": entries})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_basic_fetch():
    pages = {
        1: [_bl_entry("aaa", TS_2023)],
        2: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_beatleader(client, limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "aaa"
    assert maps[0].source == Source.BEATLEADER
    assert maps[0].stars == 4.0


@pytest.mark.asyncio
async def test_pagination():
    pages = {
        1: [_bl_entry("aaa", TS_2023)],
        2: [_bl_entry("bbb", TS_2023)],
        3: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_beatleader(client, limit=None)

    assert len(maps) == 2


@pytest.mark.asyncio
async def test_cutoff_filtering():
    pages = {
        1: [
            _bl_entry("new", TS_2023),
            _bl_entry("old", TS_2021),
        ],
    }
    async with _make_client(pages) as client:
        maps = await fetch_beatleader(client, limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "new"


@pytest.mark.asyncio
async def test_deduplication():
    pages = {
        1: [
            _bl_entry("AAA", TS_2023),
            _bl_entry("AAA", TS_2023),
        ],
        2: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_beatleader(client, limit=None)

    assert len(maps) == 1


@pytest.mark.asyncio
async def test_limit():
    pages = {
        1: [
            _bl_entry("aaa", TS_2023),
            _bl_entry("bbb", TS_2023),
            _bl_entry("ccc", TS_2023),
        ],
    }
    async with _make_client(pages) as client:
        maps = await fetch_beatleader(client, limit=2)

    assert len(maps) == 2
