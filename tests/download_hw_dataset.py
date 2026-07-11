"""Download real handwritten medical records from HuggingFace for spike testing.
Uses httpx to download parquet files directly — no datasets library needed.
"""
import shutil
from pathlib import Path

import httpx

HF_DATASET = "chaithanyakota/100-handwritten-medical-records"
PARQUET_URL = f"https://huggingface.co/datasets/{HF_DATASET}/resolve/main/data/train-00000-of-00001.parquet"
OUTPUT_DIR = Path("tests/spike_output/real_hw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Downloading {PARQUET_URL}...")
response = httpx.get(PARQUET_URL, follow_redirects=True, timeout=120.0)
response.raise_for_status()

parquet_path = OUTPUT_DIR / "train.parquet"
parquet_path.write_bytes(response.content)
print(f"Downloaded {len(response.content):,} bytes to {parquet_path}")

# Read with pandas (if available) or pyarrow
try:
    import pandas as pd
    df = pd.read_parquet(parquet_path)
    print(f"Dataset: {len(df)} rows, columns: {list(df.columns)}")

    for i, row in df.iterrows():
        if i >= 30:
            break
        img = row.get("image")
        meds = row.get("medicines", "")
        if img is not None:
            if hasattr(img, "save"):
                img.save(f"{OUTPUT_DIR}/hw_{i:03d}.png")
            elif isinstance(img, dict) and "bytes" in img:
                Path(f"{OUTPUT_DIR}/hw_{i:03d}.png").write_bytes(img["bytes"])
        status = f"[{i}] medicines: {str(meds)[:80]}" if meds else f"[{i}] saved"
        print(status)
    print(f"\nExtracted {min(30, len(df))} images to {OUTPUT_DIR}/")
except ImportError:
    print("pandas not available. Install with: pip install pandas pyarrow")
    print(f"Parquet file ready at {parquet_path}")
