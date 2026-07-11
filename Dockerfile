# TRACE OCR/NLP image — PaddleOCR-VL 1.5 (Tier 1B) + OpenMed.
# Replaces deepdoctection+DocTr (eliminated per ADR-003 / Tech Spec Part 2).
# Docling (Tier 1A) is deployed as a separate service for digital PDFs.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "numpy<2"

RUN pip install --no-cache-dir \
    "paddlepaddle>=2.6.0" \
    "paddleocr>=2.7.0"

RUN pip install --no-cache-dir \
    "openmed>=1.7.0,<1.9.0"

RUN python -c "from paddleocr import PaddleOCR; import openmed; print('PaddleOCR OK'); print('OpenMed OK'); print('ALL OK')"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
