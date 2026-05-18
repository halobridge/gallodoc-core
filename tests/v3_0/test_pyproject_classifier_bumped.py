"""Guard the supersession move #2: ``Development Status :: 4 - Beta`` in
``pyproject.toml``.

Per Decision 1 in docs/v3-design/07_decisions.md, v3 bumps the classifier
from ``3 - Alpha`` to ``4 - Beta``. The bump must not regress in future
commits.
"""

from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_PATH = PACKAGE_ROOT / "pyproject.toml"


def test_classifier_is_beta() -> None:
    cfg = tomllib.load(PYPROJECT_PATH.open("rb"))
    classifiers = cfg["project"]["classifiers"]
    assert "Development Status :: 4 - Beta" in classifiers, (
        f"expected '4 - Beta' classifier, found: {classifiers}"
    )


def test_classifier_is_not_alpha() -> None:
    cfg = tomllib.load(PYPROJECT_PATH.open("rb"))
    classifiers = cfg["project"]["classifiers"]
    assert "Development Status :: 3 - Alpha" not in classifiers, (
        "Development Status must not regress to '3 - Alpha' in v3"
    )


def test_package_version_matches_installed():
    """The version in pyproject.toml must match what importlib.metadata reports
    for the installed package. Catches drift between source and installed wheel."""
    import tomllib
    from importlib.metadata import version as _pkg_version

    with open("pyproject.toml", "rb") as fh:
        cfg = tomllib.load(fh)

    pyproject_version = cfg["project"]["version"]
    installed_version = _pkg_version("gallodoc")

    assert pyproject_version == installed_version, (
        f"pyproject.toml says {pyproject_version} but installed gallodoc reports {installed_version}"
    )
    # Sanity: must be a 3.x release
    assert pyproject_version.startswith("3."), f"Expected 3.x, got {pyproject_version}"
