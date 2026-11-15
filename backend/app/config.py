"""Application configuration.

Reads settings from environment variables (optionally loaded from a
``.env`` file at the project root).  Only non-secret settings live here;
the API deliberately never stores or loads real credentials.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Best-effort load of a ``.env`` file from the project root (if present)."""
    root = Path(__file__).resolve().parents[2]  # NexusBridge/
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        return
    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    """Runtime settings for the NexusBridge application."""

    def __init__(self) -> None:
        # Project root: NexusBridge/ (parent of this file's parents).
        self.project_root: Path = Path(__file__).resolve().parents[2]
        self.backend_root: Path = Path(__file__).resolve().parents[1]
        self.data_dir: Path = Path(os.environ.get("NEXUSBRIDGE_DATA_DIR",
                                                   self.project_root / "data"))
        self.db_path: Path = Path(os.environ.get("NEXUSBRIDGE_DB_PATH",
                                                 self.data_dir / "nexusbridge.db"))
        self.frontend_dir: Path = Path(os.environ.get("NEXUSBRIDGE_FRONTEND_DIR",
                                                      self.project_root / "frontend"))
        self.host: str = os.environ.get("NEXUSBRIDGE_HOST", "0.0.0.0")
        self.port: int = _int_env("NEXUSBRIDGE_PORT", 8000)

    def ensure_dirs(self) -> None:
        """Create the data directory if it does not yet exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton so routers share one configuration object.
settings = Settings()
settings.ensure_dirs()