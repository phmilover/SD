from analysis_service import project as project_module
from analysis_service.project import Project

from tests.helpers import make_zip


def test_single_file_is_kept_as_is():
    project = Project.load("main.py", b"print(1)")
    assert project.files == {"main.py": b"print(1)"}
    assert project.error is None


def test_zip_is_read_without_directories_and_macos_junk():
    content = make_zip({"a/main.py": "x", "__MACOSX/a/._main.py": "junk"})
    assert list(Project.load("hw.zip", content).files) == ["a/main.py"]


def test_non_zip_with_zip_extension_is_an_error():
    assert Project.load("hw.zip", b"hello").error


def test_encrypted_zip_is_an_error_not_a_crash():
    content = bytearray(make_zip({"main.py": "print(1)"}))
    # Ставим флаг «зашифровано» (бит 0) в локальном и центральном заголовках.
    content[6] |= 1
    central = content.rfind(b"PK\x01\x02")
    content[central + 8] |= 1
    project = Project.load("hw.zip", bytes(content))
    assert "паролем" in project.error


def test_unsupported_compression_is_an_error_not_a_crash():
    content = bytearray(make_zip({"main.py": "print(1)"}))
    central = content.rfind(b"PK\x01\x02")
    content[central + 10] = 99  # неизвестный метод сжатия
    content[8] = 99
    assert "Архив не читается" in Project.load("hw.zip", bytes(content)).error


def test_too_many_files_is_an_error(monkeypatch):
    monkeypatch.setattr(project_module, "MAX_FILES", 2)
    project = Project.load("hw.zip", make_zip({"a": "1", "b": "2", "c": "3"}))
    assert "больше 2 файлов" in project.error


def test_zip_bomb_is_not_unpacked(monkeypatch):
    monkeypatch.setattr(project_module, "MAX_UNPACKED_BYTES", 100)
    project = Project.load("hw.zip", make_zip({"big.txt": "0" * 1000}))
    assert project.error and not project.files


def test_text_tolerates_non_utf8():
    project = Project.load("main.py", "привет".encode("cp1251"))
    assert isinstance(project.text("main.py"), str)
