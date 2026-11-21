import io
import zipfile

import httpx

UNKNOWN_ID = "0" * 32  # корректный по формату, но несуществующий id сдачи

GOOD_PYTHON = {
    "hw/pyproject.toml": "[project]\nname = 'hw'\n",
    "hw/README.md": "# ДЗ\n",
    "hw/src/app/__init__.py": "",
    "hw/src/app/__main__.py": "print('hello')\n",
}


def make_zip(files: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def unreachable(exception: type[httpx.TransportError] = httpx.ConnectError) -> httpx.Client:
    """HTTP-клиент к «упавшему» сервису: каждый запрос заканчивается сетевой ошибкой."""

    def fail(request: httpx.Request) -> httpx.Response:
        raise exception("сервис выключен", request=request)

    return httpx.Client(base_url="http://down", transport=httpx.MockTransport(fail))
