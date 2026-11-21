import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_file_bytes: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "data/storage")),
            max_file_bytes=int(os.getenv("MAX_FILE_MB", "20")) * 1024 * 1024,
        )
