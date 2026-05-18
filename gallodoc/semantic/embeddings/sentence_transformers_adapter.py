"""Generic sentence-transformers embedding adapter.

Wraps any ``sentence_transformers.SentenceTransformer`` model — the
caller passes the model name. Lazy-imports
``sentence_transformers`` inside ``embed()`` so the package stays
lightweight when the ``[semantic]`` extra is not installed.

Typical small-model default: ``"all-MiniLM-L6-v2"`` (384 dims, fast).
"""

from __future__ import annotations

import importlib.util
from typing import Any

from gallodoc.semantic.embeddings.base import EmbeddingAdapter


_SEMANTIC_HINT = (
    "sentence_transformers adapter requires the sentence_transformers package. "
    "Install via: pip install gallodoc[semantic]"
)


class SentenceTransformersEmbeddingAdapter(EmbeddingAdapter):
    """Embeddings via any sentence-transformers model.

    Constructor takes ``model_name`` (e.g. ``"all-MiniLM-L6-v2"``) and
    an optional ``device`` (default ``"cpu"``). The model is loaded
    on the first ``embed()`` call and ``dimensions`` is populated
    once the model is loaded.
    """

    slug = "sentence_transformers"
    version = "3.0.0"

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.model_id = f"sentence_transformers:{model_name}"
        self.dimensions = 0  # resolved on first embed()
        self._model: Any = None

    @classmethod
    def available(cls) -> bool:
        """True iff sentence_transformers is importable.

        Uses ``importlib.util.find_spec`` so the check itself never
        triggers a heavyweight import.
        """
        return importlib.util.find_spec("sentence_transformers") is not None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            self._load_model()
        out = self._model.encode(texts)
        vectors = [list(map(float, v)) for v in out]
        # Update dimensions from the first vector we see — covers any
        # model the caller hands us.
        if vectors and self.dimensions == 0:
            self.dimensions = len(vectors[0])
        return vectors

    # -- internals ----------------------------------------------------

    def _load_model(self) -> None:
        if importlib.util.find_spec("sentence_transformers") is None:
            raise ImportError(_SEMANTIC_HINT)
        from sentence_transformers import SentenceTransformer  # type: ignore  # noqa: PLC0415

        self._model = SentenceTransformer(self.model_name, device=self.device)
        # Many ST models expose dimensions before encoding any text.
        get_dim = getattr(self._model, "get_sentence_embedding_dimension", None)
        if callable(get_dim):
            try:
                resolved = int(get_dim())
                if resolved > 0:
                    self.dimensions = resolved
            except Exception:  # pragma: no cover — defensive
                pass


__all__ = ["SentenceTransformersEmbeddingAdapter"]
