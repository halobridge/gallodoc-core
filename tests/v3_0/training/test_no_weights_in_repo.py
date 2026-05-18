"""Second-line guard against committed model weights.

The CI workflow lint job in ``.github/workflows/v3-release.yml`` is the
first-line scan. This pytest is the second-line scan: it walks the
``opensource/gallodoc-core/`` tree (skipping ``.git``, ``build``,
``dist``, and standard temp directories) and fails if any file ends in
``.bin``, ``.safetensors``, ``.pt``, ``.ckpt``, ``.onnx``, or ``.gguf``.

Codex prompt 07 ships the training recipe; the weights live elsewhere.
If you see this test failing, you almost certainly added a real model
artifact — move it out of the repo and reference it from the model card.
"""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]

# Extensions that flag a committed model artifact.
_WEIGHT_EXTENSIONS = (
    ".bin",
    ".safetensors",
    ".pt",
    ".ckpt",
    ".onnx",
    ".gguf",
)

# Directories the scan skips outright. Build/dist artifacts and the git
# database are noise.
_SKIP_DIRS = {
    ".git",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "venv",
    ".venv",
    "site-packages",
    ".eggs",
    "*.egg-info",
}

# Explicit allowlist for files that legitimately use a flagged extension
# (none today). Entries are paths relative to ``PACKAGE_ROOT``.
_ALLOWLIST: frozenset[str] = frozenset()


def _iter_repo_files() -> list[Path]:
    out: list[Path] = []

    def _walk(dirpath: Path) -> None:
        for entry in dirpath.iterdir():
            if entry.is_dir():
                if entry.name in _SKIP_DIRS:
                    continue
                _walk(entry)
            else:
                out.append(entry)

    _walk(PACKAGE_ROOT)
    return out


def test_no_committed_weight_artifacts(capsys):
    """Fail if any file with a weight extension is committed."""
    files = _iter_repo_files()
    offenders: list[str] = []
    for path in files:
        if path.suffix not in _WEIGHT_EXTENSIONS:
            continue
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        if rel in _ALLOWLIST:
            continue
        offenders.append(rel)

    # Friendly diagnostic on success.
    print(
        f"test_no_weights_in_repo: scanned {len(files)} files; "
        "no weight artifacts found."
    )

    assert not offenders, (
        "committed model-weight artifacts detected (see CI workflow lint "
        "job for the same scan; this is the second-line defense):\n  "
        + "\n  ".join(offenders)
    )
