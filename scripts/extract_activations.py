"""Extract residual-stream activations from Qwen2.5-7B-Instruct (base) at layer 20.

Output schema mirrors kitft/natural_language_autoencoders/nla/datagen/stage0_extract.py:
  n_raw_tokens (int64), detokenized_text_truncated (string),
  activation_vector (list<float32, 3584>), activation_layer (int64), doc_id (string)

The resulting parquet plugs directly into:
    python nla_inference.py ./actor_hf --parquet vectors.parquet

Designed for a sequential workflow on a single 24 GB GPU (e.g. RTX 4090):
  1. Run this script (loads Qwen base, ~14 GB bf16 in VRAM)
  2. Script frees VRAM on exit
  3. Launch SGLang with the NLA actor
  4. Decode with nla_inference.py --parquet

Hook pattern verified against upstream:
    natural_language_autoencoders/nla/datagen/extractors.py:70-159
"""
from __future__ import annotations

import argparse
import gc

import pyarrow as pa
import pyarrow.parquet as pq
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 3-5 generic English texts for Horizon 1 validation. Pick content-rich sentences
# (named entities, clear topics) so decodes are interpretable when read.
TEST_TEXTS: list[str] = [
    "The capital of France is Paris, a city known for its art and culture.",
    "Recipe for pasta carbonara: cook spaghetti, mix with eggs, cheese, and bacon.",
    "Machine learning models can exhibit unexpected behavior when given out-of-distribution inputs.",
    "The Roman Empire fell in the 5th century AD due to various military and economic factors.",
    "Photosynthesis converts carbon dioxide and water into glucose using sunlight.",
]

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
LAYER_INDEX = 20      # 0-indexed: hooks model.model.layers[20], captures post-block-20 residual
D_MODEL = 3584        # Qwen 7B hidden size
SKIP_FIRST = 10       # README rule: first ~10 positions decode poorly (low context accumulation)


def schema(d_model: int) -> pa.Schema:
    return pa.schema([
        ("n_raw_tokens", pa.int64()),
        ("detokenized_text_truncated", pa.string()),
        ("activation_vector", pa.list_(pa.float32(), d_model)),
        ("activation_layer", pa.int64()),
        ("doc_id", pa.string()),
    ])


def extract(texts: list[str], skip_first: int) -> list[dict]:
    print(f"[extract] Loading {MODEL_NAME} (~14 GB bf16)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, torch_dtype=torch.bfloat16, device_map="auto"
    ).eval()
    device = model.get_input_embeddings().weight.device
    print(f"[extract] Model on {device}")

    captured: list[torch.Tensor] = []

    def hook(_mod, _inp, output):
        # Decoder blocks return a tuple; first element is the residual-stream output.
        h = output[0] if isinstance(output, tuple) else output
        captured.append(h.detach().clone())

    handle = model.model.layers[LAYER_INDEX].register_forward_hook(hook)

    rows: list[dict] = []
    try:
        for doc_idx, text in enumerate(texts):
            captured.clear()
            ids = tokenizer(text, return_tensors="pt", add_special_tokens=True)["input_ids"].to(device)

            with torch.no_grad():
                model(input_ids=ids, use_cache=False)

            assert len(captured) == 1, f"hook fired {len(captured)} times for doc {doc_idx}"
            hidden = captured[0].float().cpu()[0]   # [T, d_model], fp32 on host
            token_ids = ids[0].cpu().tolist()

            kept = 0
            for pos in range(skip_first, len(token_ids)):
                rows.append({
                    "n_raw_tokens": pos + 1,
                    "detokenized_text_truncated": tokenizer.decode(
                        token_ids[: pos + 1], skip_special_tokens=True
                    ),
                    "activation_vector": hidden[pos].numpy().tolist(),
                    "activation_layer": LAYER_INDEX,
                    "doc_id": f"test_text_{doc_idx}",
                })
                kept += 1
            print(f"  [{doc_idx}] {len(token_ids)} tokens, kept {kept} (skipped first {skip_first})")
    finally:
        handle.remove()

    # Free VRAM so the caller can launch SGLang next.
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="vectors.parquet")
    ap.add_argument("--skip-first", type=int, default=SKIP_FIRST,
                    help="Skip first N positions per text (default: %(default)s — README rule)")
    args = ap.parse_args()

    rows = extract(TEST_TEXTS, args.skip_first)
    table = pa.Table.from_pylist(rows, schema=schema(D_MODEL))
    pq.write_table(table, args.output)

    print(f"\n[extract] Wrote {len(rows)} rows to {args.output}")
    print("[extract] Next steps:")
    print("  1. bash scripts/launch_sglang.sh           # in another terminal")
    print(f"  2. python nla_inference.py ./actor_hf --parquet {args.output} --n 20")


if __name__ == "__main__":
    main()
