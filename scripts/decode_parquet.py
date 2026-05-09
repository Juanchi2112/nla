"""Decode every row of a parquet via the NLA actor with rich per-row output.

Pairs with scripts/extract_activations.py — that script writes a parquet of
(doc_id, n_raw_tokens, detokenized_text_truncated, activation_vector, ...);
this one reads each row, sends activation_vector to the NLA actor, and prints
(doc, pos, ||v||, context-with-current-chunk-highlighted, decode).

Useful for Horizon 1 qualitative validation: see at a glance whether the NLA
decodes a position about "Paris" with concepts related to French geography
or to something unrelated / CJK.

Usage:
    bash scripts/launch_sglang.sh                      # in another terminal
    python scripts/decode_parquet.py ./actor_hf vectors.parquet
    python scripts/decode_parquet.py ./actor_hf vectors.parquet --n 10
    python scripts/decode_parquet.py ./actor_hf vectors.parquet --doc test_text_0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

# Allow running from repo root or from scripts/ — find nla_inference.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nla_inference import NLAClient  # noqa: E402


def format_context(prev_text: str, current_text: str) -> str:
    """Show prev_text with the new chunk wrapped in []. The bracketed part
    is the substring that was added at this position — useful to see which
    token the activation 'belongs to'."""
    if not prev_text:
        return f"[{current_text}]"
    delta = current_text[len(prev_text):]
    return f"{prev_text}[{delta}]"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkpoint", help="HF NLA actor dir (e.g. ./actor_hf)")
    ap.add_argument("parquet", help="parquet from scripts/extract_activations.py")
    ap.add_argument("--sglang-url", default="http://localhost:30000")
    ap.add_argument("--n", type=int, default=None,
                    help="Limit number of rows (default: all rows in parquet)")
    ap.add_argument("--doc", default=None,
                    help="Only decode rows where doc_id matches this value")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    args = ap.parse_args()

    client = NLAClient(args.checkpoint, sglang_url=args.sglang_url)

    table = pq.read_table(args.parquet)
    indices = list(range(len(table)))
    if args.doc is not None:
        indices = [i for i in indices if table["doc_id"][i].as_py() == args.doc]
        if not indices:
            print(f"No rows match --doc {args.doc!r}")
            return
    if args.n is not None:
        indices = indices[: args.n]

    print(f"\nDecoding {len(indices)} row(s) from {args.parquet}\n")

    # Precompute the longest text per doc for the per-document header.
    # The row with the highest n_raw_tokens for each doc has the full text.
    full_text_per_doc: dict[str, str] = {}
    for i in range(len(table)):
        doc_id = table["doc_id"][i].as_py()
        text = table["detokenized_text_truncated"][i].as_py()
        if len(text) > len(full_text_per_doc.get(doc_id, "")):
            full_text_per_doc[doc_id] = text

    prev_text_per_doc: dict[str, str] = {}
    last_doc: str | None = None

    for out_i, row_i in enumerate(indices):
        doc = table["doc_id"][row_i].as_py()

        if doc != last_doc:
            # New document — print full-text header once before its rows.
            print(f"═══ {doc} ═══")
            print(f"TEXT: {full_text_per_doc[doc]!r}")
            print()
            last_doc = doc

        pos = table["n_raw_tokens"][row_i].as_py()
        text = table["detokenized_text_truncated"][row_i].as_py()
        v = np.array(table["activation_vector"][row_i].as_py(), dtype=np.float32)

        prev = prev_text_per_doc.get(doc, "")
        ctx = format_context(prev, text)
        prev_text_per_doc[doc] = text

        norm = float(np.linalg.norm(v))
        decode = client.generate(
            v,
            temperature=args.temperature,
            max_new_tokens=args.max_new_tokens,
        )

        print(f"─── [{out_i}] pos={pos} ||v||={norm:.1f} ───")
        print(f"  context: {ctx!r}")
        print(f"  decode:  {decode}")
        print()


if __name__ == "__main__":
    main()
