"""Shared fixtures for open-source `gallodoc` tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PACKAGE_ROOT / "examples"
EXAMPLES_V11_DIR = EXAMPLES_DIR / "v1_1"
EXAMPLES_V12_DIR = EXAMPLES_DIR / "v1_2"
EXAMPLES_V13_DIR = EXAMPLES_DIR / "v1_3"
EXAMPLES_V14_DIR = EXAMPLES_DIR / "v1_4"
EXAMPLES_V15_DIR = EXAMPLES_DIR / "v1_5"
EXAMPLES_V16_DIR = EXAMPLES_DIR / "v1_6"
EXAMPLES_V20_DIR = EXAMPLES_DIR / "v2_0"


@pytest.fixture(scope="session")
def package_root() -> Path:
    return PACKAGE_ROOT


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture(scope="session")
def example_envelopes() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(EXAMPLES_DIR.glob("gallodoc_*.json")):
        out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v11() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V11_DIR.is_dir():
        for path in sorted(EXAMPLES_V11_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v12() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V12_DIR.is_dir():
        for path in sorted(EXAMPLES_V12_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v13() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V13_DIR.is_dir():
        for path in sorted(EXAMPLES_V13_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v14() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V14_DIR.is_dir():
        for path in sorted(EXAMPLES_V14_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v15() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V15_DIR.is_dir():
        for path in sorted(EXAMPLES_V15_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v16() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V16_DIR.is_dir():
        for path in sorted(EXAMPLES_V16_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def example_envelopes_v20() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if EXAMPLES_V20_DIR.is_dir():
        for path in sorted(EXAMPLES_V20_DIR.glob("*.json")):
            out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture(scope="session")
def v20_base_envelope(example_envelopes_v20: dict[str, dict]) -> dict:
    """Return the consolidated v2.0 reference envelope as the negative-test base."""
    return example_envelopes_v20["gallodoc_full_v2_reference.json"]
