"""Environment loading for the LiveKit agent."""

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load the canonical repository environment file."""
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env")
