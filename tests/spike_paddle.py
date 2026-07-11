"""Handwriting spike — PaddleOCR-VL against 30 real prescription images."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

HW_DIR = Path("tests/spike_output/real_hw")
PARQUET_PATH = HW_DIR / "train.parquet"
OUT_PATH = Path("tests/spike_output/spike_paddle_results.json")


def compute_wer(ground_truth: str, ocr_output: str) -> float:
    gt_words = ground_truth.lower().split()
    ocr_words = ocr_output.lower().split()
    if not gt_words:
        return 1.0
    gt_counter = Counter(gt_words)
    ocr_counter = Counter(ocr_words)
    matches = sum((gt_counter & ocr_counter).values())
    return 1.0 - (matches / len(gt_words))


def main():
    print("=" * 60)
    print("HANDWRITING SPIKE — PADDLEOCR-VL")
    print("=" * 60)

    from paddleocr import PaddleOCR

    engine = PaddleOCR()
    print("PaddleOCR engine initialized\n")

    df = pd.read_parquet(PARQUET_PATH)
    print(f"Ground truth records: {len(df)}")

    results = []
    for i in range(min(30, len(df))):
        row = df.iloc[i]
        ground_truth = str(row.get("medicines", "")) if pd.notna(row.get("medicines")) else ""
        if not ground_truth.strip():
            continue

        image_path = HW_DIR / f"hw_{i:03d}.png"
        if not image_path.exists():
            continue

        try:
            img = Image.open(str(image_path)).convert("RGB")
            img_np = np.array(img)
            result = engine.predict(img_np)

            texts: list[str] = []
            confidences: list[float] = []
            for item in result:
                rec_text = item.get("rec_text", "")
                rec_score = item.get("rec_score", 0.0)
                if rec_text:
                    texts.append(str(rec_text))
                    confidences.append(float(rec_score))

            ocr_text = " ".join(texts)
            mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
        except Exception as exc:
            ocr_text = ""
            mean_conf = 0.0
            print(f"  [{i}] ERROR: {exc}")

        wer = compute_wer(ground_truth, ocr_text)

        results.append({
            "id": f"hw_{i:03d}",
            "ground_truth": ground_truth[:200],
            "ocr_output": ocr_text[:200],
            "wer": wer,
            "confidence": mean_conf,
        })

        if len(results) <= 5:
            print(f"  [{i}] GT:  {ground_truth[:60]}")
            print(f"       OCR: {ocr_text[:60]}")
            print(f"       WER: {wer:.3f}  Conf: {mean_conf:.3f}\n")

    wers = [r["wer"] for r in results]
    mean_wer = sum(wers) / len(wers) if wers else 1.0
    median_wer = sorted(wers)[len(wers) // 2] if wers else 1.0

    print(f"{'=' * 60}")
    print(f"RESULTS — PADDLEOCR-VL")
    print(f"{'=' * 60}")
    print(f"Images tested: {len(results)}")
    print(f"Mean WER: {mean_wer:.3f} ({1 - mean_wer:.1%} accuracy)")
    print(f"Median WER: {median_wer:.3f}")

    if mean_wer <= 0.20:
        decision, reason = "none", "Above 80% accuracy. No cloud OCR needed."
    elif mean_wer <= 0.35:
        decision, reason = "mistral_local", "65-79%. Mistral OCR 4 Tier 2 activated."
    else:
        decision, reason = "mistral_local", "Below 65%. Mistral OCR 4 Tier 2 mandatory."

    print(f"\nDECISION: OCR_CLOUD_BACKEND = {decision}")
    print(f"Reason: {reason}")

    aggregate = {
        "engine": "PaddleOCR-VL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tested": len(results),
        "mean_wer": mean_wer,
        "median_wer": median_wer,
        "decision": decision,
        "reason": reason,
        "per_image": results,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(aggregate, f, indent=2, default=str)
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
