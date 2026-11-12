import ast
import sys
from importlib.util import resolve_name
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "pos"


@pytest.mark.parametrize(
    "layer,allowed",
    [
        ("domain", {"pos.domain"}),
        ("application", {"pos.domain", "pos.application"}),
        ("adapters", {"pos.domain", "pos.application", "pos.adapters"}),
    ],
)
def test_layers_depend_only_on_allowed_internal_modules_and_standard_library(layer, allowed):
    for path in (SOURCE / layer).rglob("*.py"):
        tree = ast.parse(path.read_text())
        package = ".".join(path.parent.relative_to(SOURCE.parent).parts)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    module = resolve_name("." * node.level + module, package)
                imports.extend(f"{module}.{alias.name}" for alias in node.names)
        for module in imports:
            root = module.split(".")[0]
            assert root in sys.stdlib_module_names or any(
                module == prefix or module.startswith(prefix + ".") for prefix in allowed
            ), (path, module)
            if layer in {"domain", "application"}:
                assert root not in {"csv", "json", "os", "pathlib", "pickle", "tempfile"}, (
                    path,
                    module,
                )
