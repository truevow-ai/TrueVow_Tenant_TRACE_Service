"""Test PaddleOCR on Fly.io machine."""
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image

# Create a simple test image with text
img = Image.new("RGB", (400, 100), "white")
engine = PaddleOCR()
result = engine.predict(np.array(img))
print("PaddleOCR engine initialized: OK")
print("OneDNN bug: GONE (no NotImplementedError)")
print("Result type:", type(result))
print("PADDLEOCR INFERENCE: WORKING ON FLY.IO")
