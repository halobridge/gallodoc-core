# LoRA export — `gallodoc-bge-m3-v1`

Companion to [`docs/specs/gallodoc-core-v3-trained-embedder.md`](../specs/gallodoc-core-v3-trained-embedder.md)
and [`docs/training/model_card_template.md`](model_card_template.md).
Documents how trained adapter weights flow OUT of the open-source
repository to an external registry. **No weights are committed in this
repo** — see the `*.safetensors` entry in the no-weights blocklist
([`tests/v3_0/training/test_no_weights_in_repo.py`](../../tests/v3_0/training/test_no_weights_in_repo.py)
and the matching lint scan in
[`.github/workflows/v3-release.yml`](../../../.github/workflows/v3-release.yml)).

## 1. What is a LoRA adapter?

LoRA — **Low-Rank Adaptation** — adds a small set of trainable rank-`r`
matrices on top of a frozen base model. Instead of fine-tuning the
hundreds of millions of parameters in `BAAI/bge-m3`, the trainer learns
only the rank-`r` deltas (typically `r = 8` or `r = 16`). The trained
artifact is a few MB rather than gigabytes, and the base model stays
canonical.

## 2. Why we ship adapters, not full weights

- **Size.** A LoRA adapter is roughly two orders of magnitude smaller
  than the full base model.
- **Distribution cost.** Smaller artifacts are cheaper to redistribute
  and cheaper to keep up-to-date.
- **Base-model stability.** The base model (`BAAI/bge-m3`) is hosted by
  its upstream; downstream releases pin the upstream HuggingFace id and
  ship only the adapter delta. Anyone reproducing our model needs the
  same base.
- **Governance.** Adapters are the unit of release. A new adapter goes
  with a new model card. The model card carries the
  `model_weights_location` URI; nothing in the open-source repository
  changes when a new adapter ships.

## 3. Output directory layout

After running `scripts/train_gallodoc_embedder.py` in `--mode standard`
or `--mode full`, the output directory looks like this:

```
weights/gallodoc_bge_m3_v1/
  <purpose>/
    adapter_config.json
    adapter_model.safetensors    # NOT committed — externally hosted
    training_log.json
    eval_report.json
```

`<purpose>` is one of the six `PURPOSE_ENUM` values:

- `document_summary_embedding`
- `relationship_embedding`
- `entity_context_embedding`
- `workflow_context_embedding`
- `risk_context_embedding`
- `policy_context_embedding`

Each purpose head ships independently. Adding a new purpose in v3.1+
does not require re-training the others.

`--mode tiny` writes only `training_log.json` (no
`adapter_model.safetensors`). Tiny is a dry-run; the log is the
artifact.

## 4. Loading a trained adapter

```python
from gallodoc.semantic.embeddings import GalloDocBgeM3V1EmbeddingAdapter

adapter = GalloDocBgeM3V1EmbeddingAdapter(
    weights_path="/path/to/weights/gallodoc_bge_m3_v1",
    purpose="document_summary_embedding",
)
vectors = adapter.embed(["text to embed"])
```

`weights_path` resolves either from the constructor argument or from
the `GALLODOC_BGE_M3_V1_WEIGHTS` environment variable. Without either,
`available()` returns `False` and `embed()` raises with a hint pointing
at `scripts/train_gallodoc_embedder.py`.

The adapter loads `<weights_path>/<purpose>/` on the first `embed()`
call. The heavy import (`sentence_transformers`, `peft`) is lazy.

## 5. Shipping adapters to a model registry

Generic — pick the registry that fits your distribution model:

- **HuggingFace Hub.** Push the per-purpose directory as a model repo.
  Reference it from the model card as
  `model_weights_location: "hf://<org>/gallodoc-bge-m3-v1"`. End users
  download via the HF CLI or the HF Python SDK.
- **S3 / GCS / Azure Blob.** Upload the directory as a versioned
  prefix. Reference it as
  `model_weights_location: "s3://<bucket>/<prefix>/v3.0.0/"`. End users
  pull with the corresponding SDK.
- **Internal registry.** Vendors with an internal model registry
  publish via their established process. The model card carries the
  internal URI.

Whichever registry you use, the open-source release pace is faster
than the model-retraining pace. The model card's `model_weights_location`
field is the only piece that changes per release; the open-source
recipe is stable.

## 6. No-weights invariant

`*.safetensors` (and `*.bin`, `*.pt`, `*.ckpt`, `*.onnx`, `*.gguf`)
are in the no-weights-scan blocklist. Two scans enforce this:

- The CI workflow lint job — fails the build on a committed weight
  artifact.
- `tests/v3_0/training/test_no_weights_in_repo.py` — second-line
  defense.

The adapter file (`adapter_model.safetensors`) lives outside this
repository. The model card carries the URI; the recipe loads from
that URI at training/inference time.
