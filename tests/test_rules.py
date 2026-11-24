"""Checks for the AGENTS.md rules that can be tested by reading the source."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Provider SDKs (decision 011 names anthropic, plus the two it considered).
PROVIDER_SDKS: frozenset[str] = frozenset({"anthropic", "openai", "litellm"})

# The one module allowed to import them (Rule 7).
LLM_MODULE = ROOT / "ragdog" / "core" / "generate.py"


def app_sources() -> list[Path]:
    """Every Python file that ships or runs the app: ragdog/, scripts/, app.py. Not tests."""
    files = [*ROOT.glob("ragdog/**/*.py"), *ROOT.glob("scripts/*.py")]
    if (ROOT / "app.py").exists():
        files.append(ROOT / "app.py")
    return sorted(files)


def imported_packages(path: Path) -> set[str]:
    """Top-level package of every import (`from anthropic.types import X` → anthropic).

    Relative imports (`from . import x`) are our own code, so they're skipped.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    packages: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            packages.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            packages.add(node.module.split(".")[0])
    return packages


def test_only_generate_imports_a_provider_sdk() -> None:
    """Rule 7: every LLM call goes through generate_answer, so no other module imports an SDK."""
    offenders = {
        str(path.relative_to(ROOT)): sorted(imported_packages(path) & PROVIDER_SDKS)
        for path in app_sources()
        if path != LLM_MODULE and imported_packages(path) & PROVIDER_SDKS
    }
    assert offenders == {}


def test_generate_is_scanned_and_does_import_anthropic() -> None:
    """Guards the test above: if the scan found no files, it would pass for the wrong reason."""
    assert LLM_MODULE in app_sources()
    assert "anthropic" in imported_packages(LLM_MODULE)
