"""Tests for ScoreSaber fetcher."""

import pytest
import httpx

from bs_map_downloader.models import Source
from bs_map_downloader.sources.scoresaber import fetch_scoresaber


def _ss_entry(song_hash: str, ranked_date: str, stars: float = 3.0) -> dict:
    return {
        "songHash": song_hash,
        "songName": f"Song {song_hash}",
        "songAuthorName": "Author",
        "levelAuthorName": "Mapper",
        "stars": stars,
        "rankedDate": ranked_date,
    }


def _make_client(pages: dict[int, list[dict]]) -> httpx.AsyncClient:
    """Build a mock client that returns paginated ScoreSaber responses."""

    async def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        entries = pages.get(page, [])
        return httpx.Response(200, json={"leaderboards": entries})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_basic_fetch():
    pages = {
        1: [_ss_entry("aaa", "2023-06-01T00:00:00Z")],
        2: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_scoresaber(client, limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "aaa"
    assert maps[0].source == Source.SCORESABER


@pytest.mark.asyncio
async def test_pagination():
    pages = {
        1: [_ss_entry("aaa", "2023-06-01T00:00:00Z")],
        2: [_ss_entry("bbb", "2023-05-01T00:00:00Z")],
        3: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_scoresaber(client, limit=None)

    assert len(maps) == 2
    assert {m.song_hash for m in maps} == {"aaa", "bbb"}


@pytest.mark.asyncio
async def test_cutoff_filtering():
    pages = {
        1: [
            _ss_entry("new", "2023-06-01T00:00:00Z"),
            _ss_entry("old", "2021-06-01T00:00:00Z"),
        ],
    }
    async with _make_client(pages) as client:
        maps = await fetch_scoresaber(client, limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "new"


@pytest.mark.asyncio
async def test_deduplication():
    pages = {
        1: [
            _ss_entry("AAA", "2023-06-01T00:00:00Z"),
            _ss_entry("AAA", "2023-05-01T00:00:00Z"),
        ],
        2: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_scoresaber(client, limit=None)

    assert len(maps) == 1


@pytest.mark.asyncio
async def test_limit():
    pages = {
        1: [
            _ss_entry("aaa", "2023-06-01T00:00:00Z"),
            _ss_entry("bbb", "2023-05-01T00:00:00Z"),
            _ss_entry("ccc", "2023-04-01T00:00:00Z"),
        ],
        2: [_ss_entry("ddd", "2023-03-01T00:00:00Z")],
    }
    async with _make_client(pages) as client:
        maps = await fetch_scoresaber(client, limit=2)

    assert len(maps) == 2
