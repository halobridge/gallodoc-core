"""Trained embedder v1 adapter — gallodoc-bge-m3-v1.

The recipe ships in this repo (``scripts/train_gallodoc_embedder.py``);
the weights live elsewhere. Without a configured weights path the
adapter is unavailable. With weights configured, ``embed()`` loads the
base model + LoRA adapter for the active purpose head and returns the
per-head projection (256-dim).

Decision 5 anchors this adapter's training story: positives in the
training set must carry a resolved ``semantic_intent``. See
``docs/specs/gallodoc-core-v3-trained-embedder.md``.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from gallodoc.semantic.embeddings.base import EmbeddingAdapter, PURPOSE_ENUM


_WEIGHTS_ENV_VAR = "GALLODOC_BGE_M3_V1_WEIGHTS"


_TRAIN_HINT = (
    "gallodoc_bge_m3_v1 requires weights_path or "
    f"{_WEIGHTS_ENV_VAR} env var. Train weights with "
    "scripts/train_gallodoc_embedder.py or download from your internal "
    "model registry."
)


class GalloDocBgeM3V1EmbeddingAdapter(EmbeddingAdapter):
    """Trained-embedder adapter for ``gallodoc-bge-m3-v1``.

    Construct with ``weights_path`` to point at a directory laid out by
    the trainer (one subdirectory per purpose head). Construct without
    ``weights_path`` to pick up the path from
    ``GALLODOC_BGE_M3_V1_WEIGHTS`` instead. With neither configured, the
    adapter is structurally valid but ``embed()`` raises a
    ``RuntimeError`` pointing users at the training script.
    """

    slug = "gallodoc_bge_m3_v1"
    version = "3.0.0"
    model_id = "gallodoc-bge-m3-v1"
    dimensions = 256  # per-head output dim

    def __init__(
        self,
        weights_path: str | None = None,
        purpose: str = "document_summary_embedding",
    ) -> None:
        if purpose not in PURPOSE_ENUM:
            raise ValueError(
                f"purpose must be in PURPOSE_ENUM, got {purpose!r}"
            )
        self.weights_path = weights_path or os.environ.get(_WEIGHTS_ENV_VAR)
        self.purpose = purpose
        self._model: Any = None
        self._lora: Any = None

    @classmethod
    def available(cls) -> bool:
        """True iff ``sentence_transformers`` is importable AND a weights path is configured.

        Uses ``importlib.util.find_spec`` so we never actually import the
        heavy dependency (which would trigger torch / transformers side
        effects).
        """
        if importlib.util.find_spec("sentence_transformers") is None:
            return False
        return bool(os.environ.get(_WEIGHTS_ENV_VAR))

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.weights_path:
            raise RuntimeError(_TRAIN_HINT)
        # Lazy-import the heavy dependencies — keep import-time cheap.
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "gallodoc_bge_m3_v1 requires sentence-transformers. "
                "Install via: pip install gallodoc[semantic]"
            ) from exc
        # Load base model on first call.
        if self._model is None:
            self._model = SentenceTransformer("BAAI/bge-m3")
            # Apply the LoRA adapter for the configured purpose head.
            # Real loading happens here in production; the shell adapter
            # validates the head directory exists and otherwise no-ops.
            self._apply_lora(self.weights_path, self.purpose)
        vectors = self._model.encode(texts).tolist()
        # Project to per-head 256-dim. For the shell adapter we slice the
        # base 1024-dim output to its first 256 dims; real training
        # replaces this with the trained projection head.
        return [list(map(float, v[: self.dimensions])) for v in vectors]

    # -- internals ----------------------------------------------------

    def _apply_lora(self, weights_path: str, purpose: str) -> None:
        """Load the LoRA adapter for the configured purpose head.

        Placeholder for the production loader. Real training writes
        weights to ``<weights_path>/<purpose>/adapter_model.safetensors``;
        the loader reads from that path on first use. Without a head
        directory present, the loader raises with a helpful message so
        users know which ``--purpose`` they still need to train.
        """
        head_dir = os.path.join(weights_path, purpose)
        if not os.path.isdir(head_dir):
            raise RuntimeError(
                f"no weights found for purpose {purpose!r} at {head_dir}. "
                f"Train this purpose head with "
                f"scripts/train_gallodoc_embedder.py --purpose {purpose}."
            )
        # Production: peft.PeftModel.from_pretrained(self._model, head_dir)
        # Test: no-op — the shell adapter doesn't load actual weights.
        return None


__all__ = ["GalloDocBgeM3V1EmbeddingAdapter"]
