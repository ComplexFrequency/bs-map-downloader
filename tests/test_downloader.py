"""Tests for download logic."""

import asyncio
import zipfile

import pytest
import httpx

from bs_map_downloader.downloader import download_all, download_map, install_maps
from bs_map_downloader.models import MapInfo, Source


def _map_info(song_hash: str = "abc123", download_url: str | None = None) -> MapInfo:
    return MapInfo(
        song_hash=song_hash,
        song_name="Test",
        song_author="Author",
        mapper="Mapper",
        ranked_date="2023-01-01",
        source=Source.SCORESABER,
        download_url=download_url,
    )


@pytest.mark.asyncio
async def test_download_map_with_known_url(tmp_path):
    zip_content = b"PK fake zip"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=zip_content)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        dest = tmp_path / "test.zip"
        sem = asyncio.Semaphore(5)
        result = await download_map(client, _map_info(download_url="https://cdn.beatsaver.com/abc.zip"), dest, sem)

    assert result is True
    assert dest.read_bytes() == zip_content


@pytest.mark.asyncio
async def test_download_map_resolves_url(tmp_path):
    zip_content = b"PK fake zip"

    async def handler(request: httpx.Request) -> httpx.Response:
        if "/maps/hash/" in str(request.url):
            return httpx.Response(200, json={
                "versions": [{"downloadURL": "https://cdn.beatsaver.com/resolved.zip"}]
            })
        return httpx.Response(200, content=zip_content)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        dest = tmp_path / "test.zip"
        sem = asyncio.Semaphore(5)
        result = await download_map(client, _map_info(), dest, sem)

    assert result is True
    assert dest.read_bytes() == zip_content


@pytest.mark.asyncio
async def test_download_map_not_found(tmp_path):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        dest = tmp_path / "test.zip"
        sem = asyncio.Semaphore(5)
        result = await download_map(client, _map_info(), dest, sem)

    assert result is False
    assert not dest.exists()


@pytest.mark.asyncio
async def test_download_map_http_error(tmp_path):
    async def handler(request: httpx.Request) -> httpx.Response:
        if "/maps/hash/" in str(request.url):
            return httpx.Response(200, json={
                "versions": [{"downloadURL": "https://cdn.beatsaver.com/fail.zip"}]
            })
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        dest = tmp_path / "test.zip"
        sem = asyncio.Semaphore(5)
        result = await download_map(client, _map_info(), dest, sem)

    assert result is False


@pytest.mark.asyncio
async def test_download_all_skips_existing(tmp_path, monkeypatch):
    import bs_map_downloader.downloader as dl_mod
    monkeypatch.setattr(dl_mod, "DOWNLOADS_DIR", tmp_path)

    # Pre-create a "downloaded" file
    existing_map = _map_info(song_hash="existing")
    (tmp_path / "existing.zip").write_bytes(b"already here")

    new_map = _map_info(song_hash="new_one", download_url="https://cdn.beatsaver.com/new.zip")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"PK new zip")

    _OrigClient = httpx.AsyncClient

    def _mock_client(**kw):
        kw.pop("transport", None)
        return _OrigClient(transport=httpx.MockTransport(handler), **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _mock_client)

    result = await download_all([existing_map, new_map])

    assert len(result) == 2
    assert (tmp_path / "new_one.zip").read_bytes() == b"PK new zip"
    # Existing file should be untouched
    assert (tmp_path / "existing.zip").read_bytes() == b"already here"


@pytest.mark.asyncio
async def test_download_all_nothing_to_do(tmp_path, monkeypatch):
    import bs_map_downloader.downloader as dl_mod
    monkeypatch.setattr(dl_mod, "DOWNLOADS_DIR", tmp_path)

    m = _map_info(song_hash="done")
    (tmp_path / "done.zip").write_bytes(b"data")

    result = await download_all([m])

    assert len(result) == 1
    assert result[0].song_hash == "done"


def _make_zip(path, files: dict[str, bytes]) -> None:
    """Create a zip file with the given name→content mapping."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_install_maps_extracts_zips(tmp_path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    install = tmp_path / "CustomLevels"

    m = _map_info(song_hash="abc123")
    _make_zip(downloads / "abc123.zip", {"info.dat": b"level data", "song.egg": b"audio"})

    install_maps([m], downloads, install)

    assert (install / "abc123" / "info.dat").read_bytes() == b"level data"
    assert (install / "abc123" / "song.egg").read_bytes() == b"audio"


def test_install_maps_skips_existing(tmp_path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    install = tmp_path / "CustomLevels"

    m = _map_info(song_hash="abc123")
    _make_zip(downloads / "abc123.zip", {"info.dat": b"new data"})

    # Pre-create the install directory
    (install / "abc123").mkdir(parents=True)
    (install / "abc123" / "info.dat").write_bytes(b"old data")

    install_maps([m], downloads, install)

    # Should not overwrite
    assert (install / "abc123" / "info.dat").read_bytes() == b"old data"


def test_install_maps_skips_missing_zip(tmp_path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    install = tmp_path / "CustomLevels"

    m = _map_info(song_hash="missing")

    install_maps([m], downloads, install)

    assert not (install / "missing").exists()
