# bs-map-downloader

Async scraper that builds a Beat Saber map dataset by downloading ranked maps from multiple leaderboard sources.

## Usage

```bash
# Download ranked maps from both ScoreSaber and BeatLeader (2022+)
uv run bs-map-downloader

# Fetch from a specific source
uv run bs-map-downloader --source scoresaber
uv run bs-map-downloader --source beatleader

# Download all maps by a specific mapper from BeatSaver
uv run bs-map-downloader --mapper noodlext

# Limit downloads per source (useful for testing)
uv run bs-map-downloader --limit 10
```

Maps are saved to `downloads/` as zip files.

The scraper is resumable — re-running skips already-downloaded files.

## Architecture

```
bs_map_downloader/
├── __init__.py          # Console and progress bar utilities
├── main.py              # CLI entry point
├── models.py            # MapInfo dataclass, Source enum, cutoff constants
├── downloader.py        # BeatSaver lookup + zip download (5 concurrent)
└── sources/
    ├── __init__.py      # Re-exports fetch functions
    ├── scoresaber.py    # ScoreSaber leaderboards API (paginated)
    ├── beatleader.py    # BeatLeader leaderboards API (paginated)
    └── beatsaver.py     # BeatSaver search API (mapper search)
```

### Data flow

1. **Fetch metadata** — Source fetchers paginate their respective APIs, filtering to maps ranked from 2022 onwards and deduplicating by song hash. Each returns a `list[MapInfo]`.
2. **Cross-source dedup** — `main.py` merges results and removes duplicates across sources.
3. **Download** — `downloader.py` resolves download URLs via the BeatSaver API (unless already known) and downloads zips with a concurrency limit of 5.

### Rate limiting

- 150ms between API pages (ScoreSaber/BeatLeader/BeatSaver)
- 100ms between individual map lookups (BeatSaver download resolution)

## External APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| ScoreSaber | `https://scoresaber.com/api/leaderboards` | Ranked map metadata |
| BeatLeader | `https://api.beatleader.xyz/leaderboards` | Ranked map metadata |
| BeatSaver | `https://api.beatsaver.com/maps/hash/{hash}` | Map download URLs |
| BeatSaver | `https://api.beatsaver.com/search/text/{page}` | Mapper search |
