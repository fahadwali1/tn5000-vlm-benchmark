#!/usr/bin/env python3
"""
Tier 1: Zero-shot inference via the OpenRouter API.

Runs a single VLM under a single prompt over the TN5000 test set.
Writes per-image predictions + raw completions to a JSONL file.

Usage
-----
export OPENROUTER_API_KEY="sk-or-v1-..."
python zero_shot_inference.py \
    --data_dir /path/to/tn5000/test_images \
    --labels /path/to/tn5000/test_labels.csv \
    --prompt prompts/baseline.txt \
    --model google/gemini-2.5-pro \
    --output results/zs_gemini25pro_baseline.jsonl \
    --max_retries 3
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI, APIError, RateLimitError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def encode_image(path: Path) -> str:
    """Read image file and return base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("ERROR: OPENROUTER_API_KEY environment variable is not set.")
    return OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)


def call_vlm(client: OpenAI, model: str, prompt_text: str, image_b64: str,
             max_retries: int = 3) -> str:
    """Call the VLM. Retry on transient errors. Returns raw completion text."""
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt_text},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ],
    }]

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=1024,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            wait = 2 ** attempt
            print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
        except APIError as e:
            print(f"  API error (attempt {attempt + 1}): {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data_dir", required=True, type=Path,
                   help="Directory containing test PNG/JPG images.")
    p.add_argument("--labels", required=True, type=Path,
                   help="CSV with columns [filename, label]; label is 0 (benign) or 1 (malignant).")
    p.add_argument("--prompt", required=True, type=Path,
                   help="Text file with the prompt template.")
    p.add_argument("--model", required=True,
                   help="OpenRouter model identifier (e.g. google/gemini-2.5-pro).")
    p.add_argument("--output", required=True, type=Path,
                   help="Output JSONL file.")
    p.add_argument("--max_retries", type=int, default=3)
    p.add_argument("--resume", action="store_true",
                   help="Skip images already present in the output file.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    prompt_text = args.prompt.read_text(encoding="utf-8")
    labels_df = pd.read_csv(args.labels)
    client = build_client()

    done: set[str] = set()
    if args.resume and args.output.exists():
        with open(args.output, "r") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["filename"])
                except Exception:
                    pass

    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if (args.resume and args.output.exists()) else "w"

    with open(args.output, mode) as out:
        for _, row in labels_df.iterrows():
            fname = row["filename"]
            label = int(row["label"])
            if fname in done:
                continue

            img_path = args.data_dir / fname
            if not img_path.exists():
                print(f"  Missing image: {img_path}", file=sys.stderr)
                continue

            try:
                img_b64 = encode_image(img_path)
                completion = call_vlm(client, args.model, prompt_text, img_b64,
                                      max_retries=args.max_retries)
            except Exception as e:
                print(f"  Error on {fname}: {e}", file=sys.stderr)
                completion = ""

            record = {
                "filename": fname,
                "label": label,
                "model": args.model,
                "prompt_file": str(args.prompt),
                "completion": completion,
            }
            out.write(json.dumps(record) + "\n")
            out.flush()

    print(f"✓ Written: {args.output}")


if __name__ == "__main__":
    main()
