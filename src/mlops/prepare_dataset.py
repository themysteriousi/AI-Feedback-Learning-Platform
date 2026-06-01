"""
Data Export Script: S3 Data Lake → DPO Preference Dataset
----------------------------------------------------------
Run this script locally (or in a Colab cell) to pull cleaned feedback
records from your S3 Data Lake and convert them into a preference dataset
ready for Direct Preference Optimization (DPO) fine-tuning.

DPO requires pairs of:
  - "chosen"  : a response that the user liked (high rating)
  - "rejected": a response that the user disliked (low rating)

Usage:
  python prepare_dataset.py \
      --bucket  your-bucket-name \
      --prefix  feedback/raw/ \
      --output  dpo_dataset.jsonl \
      --min-rating-gap 2
"""

import boto3
import json
import argparse
import os
from pathlib import Path
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
CHOSEN_MIN_STARS  = 4   # Responses rated ≥ 4 stars are "chosen"
REJECTED_MAX_STARS = 2  # Responses rated ≤ 2 stars are "rejected"
# ─────────────────────────────────────────────────────────────────────────────


def fetch_all_records(s3_client, bucket: str, prefix: str) -> list[dict]:
    """Download and parse all JSON feedback records from S3."""
    records = []
    paginator = s3_client.get_paginator("list_objects_v2")

    print(f"📥  Scanning s3://{bucket}/{prefix} ...")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
            try:
                records.append(json.loads(body))
            except json.JSONDecodeError:
                print(f"  ⚠️  Skipping malformed record: {key}")

    print(f"✅  Loaded {len(records)} feedback records from S3.")
    return records


def build_preference_pairs(records: list[dict], min_rating_gap: int) -> list[dict]:
    """
    Group records by their prompt, then form chosen/rejected pairs.
    A pair is valid only if the rating gap is >= min_rating_gap.
    """
    by_prompt = defaultdict(lambda: {"chosen": [], "rejected": []})

    for rec in records:
        prompt  = rec.get("prompt", "").strip()
        response = rec.get("response", "").strip()
        rating  = rec.get("star_rating")
        thumbs  = rec.get("thumbs")

        if not prompt or not response:
            continue

        # Determine quality using star rating if available, fallback to thumbs
        if rating is not None:
            if int(rating) >= CHOSEN_MIN_STARS:
                by_prompt[prompt]["chosen"].append(response)
            elif int(rating) <= REJECTED_MAX_STARS:
                by_prompt[prompt]["rejected"].append(response)
        elif thumbs == "up":
            by_prompt[prompt]["chosen"].append(response)
        elif thumbs == "down":
            by_prompt[prompt]["rejected"].append(response)

    pairs = []
    for prompt, group in by_prompt.items():
        for chosen in group["chosen"]:
            for rejected in group["rejected"]:
                # Format compatible with Hugging Face trl DPOTrainer
                pairs.append({
                    "prompt":   prompt,
                    "chosen":   chosen,
                    "rejected": rejected,
                })

    print(f"🔗  Built {len(pairs)} preference pairs from {len(by_prompt)} unique prompts.")
    return pairs


def save_dataset(pairs: list[dict], output_path: str):
    """Save preference pairs as JSONL for easy streaming into the trainer."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    print(f"💾  Saved {len(pairs)} pairs → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export S3 feedback to DPO dataset")
    parser.add_argument("--bucket",          required=True,                 help="S3 bucket name")
    parser.add_argument("--prefix",          default="feedback/raw/",       help="S3 key prefix")
    parser.add_argument("--output",          default="data/dpo_dataset.jsonl", help="Output JSONL path")
    parser.add_argument("--min-rating-gap",  type=int, default=2,           help="Min star gap for pairs")
    args = parser.parse_args()

    s3 = boto3.client("s3")
    records = fetch_all_records(s3, args.bucket, args.prefix)

    if not records:
        print("❌  No records found. Have you collected any feedback yet?")
        return

    pairs = build_preference_pairs(records, args.min_rating_gap)

    if not pairs:
        print("❌  Not enough contrasting pairs yet. Collect more feedback with varied ratings!")
        return

    save_dataset(pairs, args.output)
    print(f"\n✨  Dataset ready! Upload data/dpo_dataset.jsonl to Google Colab to begin training.")


if __name__ == "__main__":
    main()
