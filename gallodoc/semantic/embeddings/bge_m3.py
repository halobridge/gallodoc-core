"""bge_m3 embedding adapter — lazy-imported behind the [semantic] extra.

Wraps the ``BAAI/bge-m3`` model. Two backends are supported:

1. ``FlagEmbedding.BGEM3FlagModel`` — preferred when available.
2. ``sentence_transformers.SentenceTransformer("BAAI/bge-m3")`` —
   fallback when only the ``[semantic]`` extra is installed.

Either backend works; the adapter picks whichever is importable.

Heavy imports happen inside ``embed()`` so just importing the package
stays lightweight. ``available()`` does a no-op import check and never
loads model weights.
"""

from __future__ import annotations

import importlib.util
from typing import Any

from gallodoc.semantic.embeddings.base import EmbeddingAdapter


_SEMANTIC_HINT = (
    "bge_m3 adapter requires either FlagEmbedding or sentence_transformers. "
    "Install via: pip install gallodoc[semantic]"
)


class BgeM3EmbeddingAdapter(EmbeddingAdapter):
    """Embeddings via BAAI/bge-m3.

    Constructor takes an optional ``device`` (default ``"cpu"``). The
    actual model is loaded on the first ``embed()`` call and cached on
    the instance.
    """

    slug = "bge_m3"
    version = "3.0.0"
    model_id = "BAAI/bge-m3"
    dimensions = 1024

    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self._model: Any = None
        self._backend: str = ""

    @classmethod
    def available(cls) -> bool:
        """True iff FlagEmbedding OR sentence_transformers is importable.

        Uses ``importlib.util.find_spec`` so we never actually import
        the dependency (which would trigger torch/transformers
        side-effects).
        """
        return (
            importlib.util.find_spec("FlagEmbedding") is not None
            or importlib.util.find_spec("sentence_transformers") is not None
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            self._load_model()
        if self._backend == "flag_embedding":
            return self._embed_via_flag_embedding(texts)
        return self._embed_via_sentence_transformers(texts)

    # -- internals ----------------------------------------------------

    def _load_model(self) -> None:
        # Prefer FlagEmbedding — it's the upstream BAAI implementation.
        if importlib.util.find_spec("FlagEmbedding") is not None:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore  # noqa: PLC0415

            self._model = BGEM3FlagModel(
                self.model_id,
                use_fp16=False,
                device=self.device,
            )
            self._backend = "flag_embedding"
            return
        if importlib.util.find_spec("sentence_transformers") is not None:
            from sentence_transformers import SentenceTransformer  # type: ignore  # noqa: PLC0415

            self._model = SentenceTransformer(self.model_id, device=self.device)
            self._backend = "sentence_transformers"
            return
        raise ImportError(_SEMANTIC_HINT)

    def _embed_via_flag_embedding(self, texts: list[str]) -> list[list[float]]:
        # BGEM3FlagModel.encode returns a dict with "dense_vecs" entries.
        out = self._model.encode(texts)
        dense = out["dense_vecs"] if isinstance(out, dict) else out
        return [list(map(float, v)) for v in dense]

    def _embed_via_sentence_transformers(
        self, texts: list[str]
    ) -> list[list[float]]:
        out = self._model.encode(texts)
        # ``encode`` returns numpy arrays; ``.tolist()`` is supported on
        # both ndarray and torch tensor outputs.
        return [list(map(float, v)) for v in out]


__all__ = ["BgeM3EmbeddingAdapter"]
