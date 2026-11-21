import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    storage_url: str
    http_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "data/analysis")),
            storage_url=os.getenv("STORAGE_URL", "http://localhost:8001"),
            http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "5")),
        )
