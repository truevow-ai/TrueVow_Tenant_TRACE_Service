# TRACE image — Mistral OCR 4 + Tesseract + OpenMed.
# Tier 1B OCR: Mistral OCR 4 self-hosted (Fly.io sidecar, no BAA, no per-page cost).
# Tier 1B fallback: Tesseract (local, always available).
# Replaces PaddleOCR-VL (eliminated — oneDNN cross-platform bug).
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "openmed>=1.7.0,<1.9.0" \
    "mistralai>=1.0.0" \
    "pytesseract>=0.3.10" \
    "pymupdf>=1.23.0"

RUN python -c "import openmed; import pytesseract; print('OpenMed OK'); print('Tesseract OK'); print('ALL OK')"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
