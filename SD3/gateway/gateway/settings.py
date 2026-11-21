import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    storage_url: str
    analysis_url: str
    http_timeout_seconds: float
    max_upload_bytes: int = 20 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            storage_url=os.getenv("STORAGE_URL", "http://localhost:8001"),
            analysis_url=os.getenv("ANALYSIS_URL", "http://localhost:8002"),
            http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "10")),
            max_upload_bytes=int(os.getenv("MAX_FILE_MB", "20")) * 1024 * 1024,
        )
