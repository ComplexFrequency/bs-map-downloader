"""Beat Saber ranked map scraper package."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def fetch_progress(label: str, **extra_columns: str) -> Progress:
    """Create a reusable progress bar for fetch functions.

    Args:
        label: Bold blue label text (e.g. "Fetching ScoreSaber leaderboards...")
        **extra_columns: Additional task field columns as format strings
                         (e.g. page="page {task.fields[page]}")
    """
    columns = [
        SpinnerColumn(),
        TextColumn(f"[bold blue]{label}"),
        *[TextColumn(fmt) for fmt in extra_columns.values()],
    ]
    return Progress(*columns, console=console)
