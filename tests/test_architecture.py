"""cms never imports a sibling module — media, forms and translation are names."""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
FORBIDDEN = ("stapel_docs", "stapel_forms", "stapel_cdn", "stapel_translate", "stapel_feed", "stapel_listings",
             "stapel_search", "stapel_auth", "stapel_notifications", "stapel_realtime", "stapel_profiles",
             "stapel_orders", "stapel_shop")


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            yield node.module


def _sources():
    for path in PACKAGE.rglob("*.py"):
        rel = path.relative_to(PACKAGE).parts
        if rel[0] in ("tests", "e2e", "build", "dist", ".venv") or ".egg-info" in str(path):
            continue
        yield path


def test_no_sibling_import_anywhere():
    offenders = [(str(p.relative_to(PACKAGE)), name) for p in _sources() for name in _imports(p)
                 if name.split(".")[0] in FORBIDDEN]
    assert offenders == []


def test_the_scan_sees_the_package():
    names = {p.name for p in _sources()}
    assert {"models.py", "blocks.py", "views.py", "content.py", "public.py"} <= names


def test_the_rule_fires_on_a_sibling_import(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("from stapel_cdn.models import Image\n")
    assert list(_imports(bad)) == ["stapel_cdn.models"]
