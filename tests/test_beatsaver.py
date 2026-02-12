"""Tests for BeatSaver mapper search fetcher."""

import pytest
import httpx

from bs_map_downloader.models import Source
from bs_map_downloader.sources.beatsaver import fetch_mapper


def _bs_doc(song_hash: str, mapper: str = "TestMapper") -> dict:
    return {
        "versions": [
            {
                "hash": song_hash,
                "downloadURL": f"https://cdn.beatsaver.com/{song_hash}.zip",
            }
        ],
        "metadata": {
            "songName": f"Song {song_hash}",
            "songAuthorName": "Author",
            "levelAuthorName": mapper,
        },
        "uploaded": "2023-06-01T00:00:00+00:00",
    }


def _make_client(pages: dict[int, list[dict]]) -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        # URL is like /search/text/{page}
        page = int(request.url.path.split("/")[-1])
        docs = pages.get(page, [])
        return httpx.Response(200, json={"docs": docs})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_basic_fetch():
    pages = {
        0: [_bs_doc("aaa")],
        1: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_mapper(client, "TestMapper", limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "aaa"
    assert maps[0].source == Source.BEATSAVER
    assert maps[0].download_url == "https://cdn.beatsaver.com/aaa.zip"


@pytest.mark.asyncio
async def test_pagination():
    pages = {
        0: [_bs_doc("aaa")],
        1: [_bs_doc("bbb")],
        2: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_mapper(client, "TestMapper", limit=None)

    assert len(maps) == 2


@pytest.mark.asyncio
async def test_limit():
    pages = {
        0: [_bs_doc("aaa"), _bs_doc("bbb"), _bs_doc("ccc")],
    }
    async with _make_client(pages) as client:
        maps = await fetch_mapper(client, "TestMapper", limit=2)

    assert len(maps) == 2


@pytest.mark.asyncio
async def test_skips_entries_without_versions():
    pages = {
        0: [
            {"versions": [], "metadata": {}, "uploaded": ""},
            _bs_doc("aaa"),
        ],
        1: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_mapper(client, "TestMapper", limit=None)

    assert len(maps) == 1
    assert maps[0].song_hash == "aaa"


@pytest.mark.asyncio
async def test_skips_entries_without_hash():
    pages = {
        0: [
            {
                "versions": [{"hash": "", "downloadURL": "https://example.com"}],
                "metadata": {},
                "uploaded": "",
            },
            _bs_doc("aaa"),
        ],
        1: [],
    }
    async with _make_client(pages) as client:
        maps = await fetch_mapper(client, "TestMapper", limit=None)

    assert len(maps) == 1
