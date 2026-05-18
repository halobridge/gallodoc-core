"""Open embeddings adapter package.

Re-exports the public interface, helpers, starter adapters, the
``apply_embeddings`` envelope-integration entry point, and the
``EMBEDDING_ADAPTERS`` registry the CLI dispatches on.

Heavy adapters (``bge_m3``, ``sentence_transformers``) are imported at
module level, but their optional dependencies are NOT — heavy imports
happen inside each adapter's ``embed()`` call. See
``docs/specs/gallodoc-core-v3-embeddings.md`` for the spec.
"""

from gallodoc.semantic.embeddings.apply import apply_embeddings
from gallodoc.semantic.embeddings.base import (
    EmbeddingAdapter,
    EmbeddingRecord,
    PURPOSE_ENUM,
    hash_vector,
    now_iso,
    validate_purpose,
)
from gallodoc.semantic.embeddings.bge_m3 import BgeM3EmbeddingAdapter
from gallodoc.semantic.embeddings.local_stub import LocalStubEmbeddingAdapter
from gallodoc.semantic.embeddings.sentence_transformers_adapter import (
    SentenceTransformersEmbeddingAdapter,
)
from gallodoc.semantic.embeddings.trained import GalloDocBgeM3V1EmbeddingAdapter


# Adapter registry — keyed by slug. The CLI dispatches by this map.
# Keep alphabetical for deterministic --help output.
EMBEDDING_ADAPTERS: dict[str, type[EmbeddingAdapter]] = {
    "bge_m3": BgeM3EmbeddingAdapter,
    "gallodoc_bge_m3_v1": GalloDocBgeM3V1EmbeddingAdapter,
    "local_stub": LocalStubEmbeddingAdapter,
    "sentence_transformers": SentenceTransformersEmbeddingAdapter,
}


__all__ = [
    "BgeM3EmbeddingAdapter",
    "EMBEDDING_ADAPTERS",
    "EmbeddingAdapter",
    "EmbeddingRecord",
    "GalloDocBgeM3V1EmbeddingAdapter",
    "LocalStubEmbeddingAdapter",
    "PURPOSE_ENUM",
    "SentenceTransformersEmbeddingAdapter",
    "apply_embeddings",
    "hash_vector",
    "now_iso",
    "validate_purpose",
]
