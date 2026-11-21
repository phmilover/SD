"""Сданный файл в виде, удобном для проверок: один исходник или содержимое zip-архива."""

import io
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import PurePosixPath

# Архив не распаковывается на диск, а читается в память, поэтому ограничиваем zip-бомбы.
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_FILES = 2000

# Всё, чем zipfile сообщает о битом или неподдерживаемом архиве (метод сжатия, пароль, обрыв).
ARCHIVE_ERRORS = (
    zipfile.BadZipFile,
    ValueError,
    RuntimeError,
    NotImplementedError,
    EOFError,
    zlib.error,
)


@dataclass(frozen=True)
class Project:
    filename: str
    size_bytes: int
    files: dict[str, bytes] = field(default_factory=dict)  # путь внутри сдачи → содержимое
    error: str | None = None  # почему содержимое не удалось прочитать

    @classmethod
    def load(cls, filename: str, content: bytes) -> "Project":
        size = len(content)
        if not content:
            return cls(filename, size)
        if not zipfile.is_zipfile(io.BytesIO(content)):
            if filename.lower().endswith(".zip"):
                return cls(filename, size, error="Файл .zip повреждён или не является архивом")
            return cls(filename, size, files={filename: content})
        try:
            return cls(filename, size, files=_unpack(content))
        except ARCHIVE_ERRORS as error:
            return cls(filename, size, error=f"Архив не читается: {error}")

    def paths(self) -> list[PurePosixPath]:
        return [PurePosixPath(path) for path in self.files]

    def text(self, path: str) -> str:
        return self.files[path].decode("utf-8", errors="replace")


def _unpack(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = [
            info
            for info in archive.infolist()
            if not info.is_dir() and not info.filename.startswith("__MACOSX/")
        ]
        if any(info.flag_bits & 0x1 for info in entries):
            raise ValueError("архив защищён паролем")
        if len(entries) > MAX_FILES:
            raise ValueError(f"больше {MAX_FILES} файлов")
        if sum(info.file_size for info in entries) > MAX_UNPACKED_BYTES:
            raise ValueError(f"после распаковки больше {MAX_UNPACKED_BYTES // 2**20} МБ")
        return {info.filename: archive.read(info) for info in entries}
