"""Mistral OCR smoke test against all 30 prescription images."""
import json, os, base64
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

from mistralai.client import Mistral

HW_DIR = Path("/app/tests/spike_output/real_hw")
PARQUET_PATH = HW_DIR / "train.parquet"
OUT_PATH = Path("/app/tests/spike_output/mistral_spike_results.json")


def compute_wer(gt, ocr):
    gt_words = gt.lower().split()
    ocr_words = ocr.lower().split()
    if not gt_words:
        return 1.0
    matches = sum((Counter(gt_words) & Counter(ocr_words)).values())
    return 1.0 - (matches / len(gt_words))


def main():
    import pandas as pd

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY not set")
        return

    print("=" * 60)
    print("HANDWRITING SPIKE — MISTRAL OCR 4")
    print("=" * 60)

    client = Mistral(api_key=api_key)
    print("Client initialized\n")

    df = pd.read_parquet(PARQUET_PATH)
    print(f"Ground truth records: {len(df)}")

    results = []
    for i in range(min(30, len(df))):
        row = df.iloc[i]
        gt = str(row.get("medicines", "")) if pd.notna(row.get("medicines")) else ""
        if not gt.strip():
            continue

        img_path = HW_DIR / f"hw_{i:03d}.png"
        if not img_path.exists():
            continue

        try:
            with open(img_path, "rb") as f:
                b = base64.b64encode(f.read()).decode()
            r = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": f"data:image/png;base64,{b}"},
                include_image_base64=False,
            )
            text = r.pages[0].markdown.strip() if r.pages else ""
            cs = r.pages[0].confidence_scores
            conf = cs.average_page_confidence_score if cs else 0.95
        except Exception as exc:
            text = ""
            conf = 0.0
            print(f"  [{i}] ERROR: {type(exc).__name__}")

        wer = compute_wer(gt, text)
        results.append({"id": f"hw_{i:03d}", "ground_truth": gt[:200], "ocr_output": text[:200], "wer": wer, "confidence": conf})

        if len(results) <= 5:
            print(f"  [{i}] GT:  {gt[:60]}")
            print(f"       OCR: {text[:60]}")
            print(f"       WER: {wer:.3f}  Conf: {conf:.3f}\n")

    wers = [r["wer"] for r in results]
    mean_wer = sum(wers) / len(wers) if wers else 1.0
    median_wer = sorted(wers)[len(wers) // 2] if wers else 1.0

    print(f"  ---")
    print(f"  Images: {len(results)}")
    print(f"  Mean WER: {mean_wer:.3f} ({1 - mean_wer:.1%} accuracy)")
    print(f"  Median WER: {median_wer:.3f}")

    if mean_wer <= 0.20:
        decision, reason = "none", "Above 80% accuracy."
    elif mean_wer <= 0.35:
        decision, reason = "mistral_local", "65-79%."
    else:
        decision, reason = "mistral_local", "Below 65%."

    print(f"  DECISION: OCR_CLOUD_BACKEND = {decision}")
    print(f"  Reason: {reason}")

    aggregate = {
        "engine": "Mistral-OCR-4",
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
    print(f"  Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
