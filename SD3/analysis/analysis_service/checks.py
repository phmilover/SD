"""Эвристические проверки «на собираемость».

Проверка — это функция `Project -> CheckResult`. Новая проверка = новая функция
и одна строка в `DEFAULT_CHECKS`; анализатор и API при этом не меняются.
"""

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel

from .project import Project

Status = Literal["passed", "failed", "warning", "skipped"]

LANGUAGES = {
    ".py": "Python",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".js": "JavaScript",
    ".ts": "TypeScript",
}

BUILD_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "CMakeLists.txt",
    "Makefile",
    "package.json",
    "go.mod",
    "Cargo.toml",
}
BUILD_SUFFIXES = {".csproj", ".sln"}

ENTRY_POINTS = {
    "Python": re.compile(r"""if\s+__name__\s*==\s*['"]__main__['"]"""),
    "Java": re.compile(r"static\s+void\s+main\s*\("),
    "Kotlin": re.compile(r"\bfun\s+main\s*\("),
    "C#": re.compile(r"\bstatic\s+(async\s+)?\w+\s+Main\s*\("),
    "C": re.compile(r"\bint\s+main\s*\("),
    "C++": re.compile(r"\bint\s+main\s*\("),
    "Go": re.compile(r"\bfunc\s+main\s*\(\s*\)"),
    "Rust": re.compile(r"\bfn\s+main\s*\(\s*\)"),
}

# Python-скрипт запускается и без `if __name__ == "__main__"`: `python main.py`, `python -m app`.
PYTHON_SCRIPT_NAMES = {"__main__.py", "main.py", "app.py"}


class CheckResult(BaseModel):
    name: str
    title: str
    status: Status
    message: str


@dataclass(frozen=True)
class Check:
    name: str
    title: str
    run: Callable[[Project], tuple[Status, str]]
    blocking: bool = False  # при провале дальше проверять нечего

    def __call__(self, project: Project) -> CheckResult:
        status, message = self.run(project)
        return CheckResult(name=self.name, title=self.title, status=status, message=message)


def source_files(project: Project) -> list[str]:
    return [p for p in project.files if _suffix(p) in LANGUAGES and not _is_vendor(p)]


def detect_language(project: Project) -> str | None:
    counts = Counter(LANGUAGES[_suffix(path)] for path in source_files(project))
    return counts.most_common(1)[0][0] if counts else None


def not_empty(project: Project) -> tuple[Status, str]:
    if project.size_bytes == 0:
        return "failed", "Файл пустой (0 Б)"
    return "passed", f"Размер {project.size_bytes} Б"


def readable(project: Project) -> tuple[Status, str]:
    if project.error:
        return "failed", project.error
    return "passed", f"Файлов в сдаче: {len(project.files)}"


def has_source_code(project: Project) -> tuple[Status, str]:
    sources = source_files(project)
    if not sources:
        return "failed", "Нет ни одного файла с исходным кодом"
    return "passed", f"{detect_language(project)}: {len(sources)} файл(ов) с кодом"


def has_build_file(project: Project) -> tuple[Status, str]:
    found = sorted(
        path.name
        for path in project.paths()
        if path.name in BUILD_FILES or path.suffix in BUILD_SUFFIXES
    )
    if not found:
        return "warning", "Нет файла сборки или зависимостей (pyproject.toml, pom.xml, …)"
    return "passed", ", ".join(found)


def has_entry_point(project: Project) -> tuple[Status, str]:
    language = detect_language(project)
    pattern = ENTRY_POINTS.get(language or "")
    if pattern is None:
        return "skipped", f"Для языка {language} точка входа не проверяется"
    for path in source_files(project):
        if pattern.search(project.text(path)) or (
            language == "Python" and PurePosixPath(path).name.lower() in PYTHON_SCRIPT_NAMES
        ):
            return "passed", f"Найдена в {path}"
    return "failed", f"Не найдена точка входа {language}-программы (main)"


def python_syntax(project: Project) -> tuple[Status, str]:
    sources = [path for path in source_files(project) if _suffix(path) == ".py"]
    if not sources:
        return "skipped", "Нет файлов .py"
    for path in sources:
        try:
            # compile() только разбирает код в байт-код и ничего не выполняет.
            compile(project.files[path], path, "exec", dont_inherit=True)
        except SyntaxError as error:
            where = f"{path}, строка {error.lineno}" if error.lineno else path
            return "failed", f"{where}: {error.msg}"
        except (ValueError, RecursionError, MemoryError) as error:  # слишком сложный или бинарный
            return "failed", f"{path}: {error}"
    return "passed", f"Синтаксис в порядке ({len(sources)} файл(ов))"


def has_readme(project: Project) -> tuple[Status, str]:
    if any(path.name.lower().startswith("readme") for path in project.paths()):
        return "passed", "README есть"
    return "warning", "Нет README"


DEFAULT_CHECKS: tuple[Check, ...] = (
    Check("not_empty", "Файл не пустой", not_empty, blocking=True),
    Check("readable", "Содержимое читается", readable, blocking=True),
    Check("source_code", "Есть исходный код", has_source_code, blocking=True),
    Check("build_file", "Есть файл сборки", has_build_file),
    Check("entry_point", "Есть точка входа", has_entry_point),
    Check("python_syntax", "Python компилируется", python_syntax),
    Check("readme", "Есть README", has_readme),
)


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _is_vendor(path: str) -> bool:
    parts = path.split("/")
    return any(part in {".venv", "venv", "node_modules", "__pycache__", "build"} for part in parts)
