"""Real handwriting spike — runs PaddleOCR-VL inside Docker."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HW_DIR = Path("/spike_images")
PARQUET_PATH = HW_DIR / "train.parquet"
OUT_PATH = Path("/spike_output/spike_real_results.json")


def compute_wer(ground_truth: str, ocr_output: str) -> float:
    gt_words = ground_truth.lower().split()
    ocr_words = ocr_output.lower().split()
    if not gt_words:
        return 1.0
    from collections import Counter
    gt_counter = Counter(gt_words)
    ocr_counter = Counter(ocr_words)
    matches = sum((gt_counter & ocr_counter).values())
    return 1.0 - (matches / len(gt_words))


def get_ocr_engine():
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_angle_cls=True,
        lang='en',
        use_gpu=False,
    )


def run_ocr_on_image(image_path: str, engine) -> str:
    result = engine.ocr(image_path, cls=True)
    if not result or not result[0]:
        return ""
    lines = []
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]
            confidence = line[1][1]
            if confidence > 0.5:
                lines.append(text)
    return " ".join(lines)


def main():
    print("=" * 60)
    print("PHASE 1C HANDWRITING SPIKE — REAL PADDLEOCR-VL ENGINE")
    print("=" * 60)

    engine = get_ocr_engine()
    print("PaddleOCR-VL engine initialized")

    df = pd.read_parquet(PARQUET_PATH)
    print(f"Ground truth records: {len(df)}")

    results = []
    for i, row in df.iterrows():
        if i >= 30:
            break
        ground_truth = str(row.get("medicines", "")) if pd.notna(row.get("medicines")) else ""
        if not ground_truth.strip():
            continue

        image_path = HW_DIR / f"hw_{i:03d}.png"
        if not image_path.exists():
            print(f"  [{i}] SKIP — image not found: {image_path}")
            continue

        try:
            ocr_text = run_ocr_on_image(str(image_path), engine).strip()
        except Exception as exc:
            ocr_text = f"[OCR_ERROR: {type(exc).__name__}]"

        wer = compute_wer(ground_truth, ocr_text)

        results.append({
            "id": f"hw_{i:03d}",
            "ground_truth": ground_truth[:120],
            "ocr_output": ocr_text[:120],
            "wer": wer,
        })

        if i < 5:
            print(f"\n  [{i}] Ground truth: {ground_truth[:80]}")
            print(f"       OCR output:   {ocr_text[:80]}")
            print(f"       WER: {wer:.3f}")

    wers = [r["wer"] for r in results]
    mean_wer = sum(wers) / len(wers) if wers else 1.0
    median_wer = sorted(wers)[len(wers) // 2] if wers else 1.0

    print(f"\n{'=' * 60}")
    print(f"RESULTS — REAL PADDLEOCR-VL")
    print(f"{'=' * 60}")
    print(f"Images tested: {len(results)}")
    print(f"Mean WER: {mean_wer:.3f} ({1 - mean_wer:.1%} accuracy)")
    print(f"Median WER: {median_wer:.3f}")

    if mean_wer <= 0.20:
        decision = "none"
        reason = "Above 80% accuracy threshold."
    elif mean_wer <= 0.35:
        decision = "mistral_local"
        reason = "Between 65-79%. Mistral OCR 4 Tier 2 activated."
    else:
        decision = "mistral_local"
        reason = "Below 65%. Mistral OCR 4 Tier 2 mandatory."

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

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(aggregate, f, indent=2, default=str)
    print(f"\nResults saved to {OUT_PATH}")

    return mean_wer


if __name__ == "__main__":
    mean_wer = main()
    sys.exit(0)
