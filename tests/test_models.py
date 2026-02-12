"""Tests for MapInfo model."""

from bs_map_downloader.models import CUTOFF_DATE, CUTOFF_TIMESTAMP, MapInfo, Source


def test_to_metadata():
    m = MapInfo(
        song_hash="abc123",
        song_name="Test Song",
        song_author="Artist",
        mapper="Mapper",
        ranked_date="2023-01-01T00:00:00+00:00",
        source=Source.SCORESABER,
        stars=5.5,
    )
    meta = m.to_metadata()
    assert meta == {
        "songHash": "abc123",
        "songName": "Test Song",
        "songAuthorName": "Artist",
        "levelAuthorName": "Mapper",
        "stars": 5.5,
        "rankedDate": "2023-01-01T00:00:00+00:00",
        "source": "scoresaber",
    }


def test_to_metadata_defaults():
    m = MapInfo(
        song_hash="abc",
        song_name="",
        song_author="",
        mapper="",
        ranked_date="",
        source=Source.BEATSAVER,
    )
    meta = m.to_metadata()
    assert meta["stars"] == 0.0
    assert meta["source"] == "beatsaver"


def test_cutoff_constants():
    assert CUTOFF_DATE.year == 2022
    assert CUTOFF_TIMESTAMP == int(CUTOFF_DATE.timestamp())
