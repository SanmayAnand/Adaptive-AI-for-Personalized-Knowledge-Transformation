# tests/backend/test_ocr.py — Person B runs this locally
#
# Prerequisites:
#   pip install pdfplumber boto3
#   aws configure   (use keys from Person A)
#   aws s3 cp yourfile.pdf s3://akte-bucket/uploads/yourfile.pdf
#
# Run: python3 tests/backend/test_ocr.py

import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/lambda-main'))

from ocr import extract_text

BUCKET = 'akte-bucket'
TEST_KEY = 'uploads/yourfile.pdf'   # change to a real uploaded file

if __name__ == '__main__':
    print(f"Testing OCR on s3://{BUCKET}/{TEST_KEY}")
    text = extract_text(BUCKET, TEST_KEY)
    print(f"\nCharacters extracted: {len(text)}")
    print(f"Words: {len(text.split())}")
    print("\n--- First 500 characters ---")
    print(text[:500])
    print("\n--- Last 200 characters ---")
    print(text[-200:])
    print("\n✓ OCR test passed" if len(text) > 100 else "\n✗ OCR returned too little text")
