# ocr.py — Person B owns this entirely
# Lambda: akte-main (placed here by Person A when received)
#
# Public API (Person A calls this):
#   extract_text(bucket: str, key: str) -> str
#
# What it does:
#   1. Download PDF bytes from S3 at bucket/key
#   2. Try pdfplumber (_digital): extracts text from text-based PDFs page by page
#      - If pages_with_text == 0 OR total extracted text < 150 chars → PDF is likely scanned
#   3. Fallback to AWS Textract (_scanned): OCR for scanned/image PDFs
#      - Uses textract.detect_document_text with S3Object reference
#      - Joins all LINE blocks into a string
#   4. Clean the raw text (_clean):
#      - Strip blank lines
#      - Remove lone page numbers (regex: ^\d{1,4}$)
#      - Remove decorative lines (regex: ^[-._=]{3,}$)
#      - Remove short fragments < 4 words unless they look like headings (istitle or isupper)
#      - Collapse 3+ consecutive newlines to 2
#   5. Raise ValueError if result is empty — lets main_handler return a 500 error
#
# Clients (boto3):
#   s3 = boto3.client('s3')
#   textract = boto3.client('textract', region_name='us-east-1')
#
# Private helpers to implement:
#   _download(bucket, key) -> bytes
#   _digital(pdf_bytes) -> (text: str, pages_with_text: int)
#   _scanned(bucket, key) -> str
#   _clean(text) -> str
#   extract_text(bucket, key) -> str   ← THIS IS THE ONLY PUBLIC FUNCTION
#
# IMPORTANT: The function name must be exactly extract_text(bucket, key).
#            main_handler.py imports it as: from ocr import extract_text
#            Do NOT rename it.
#
# Test locally:
#   aws s3 cp yourfile.pdf s3://akte-bucket/uploads/yourfile.pdf
#   python3 -c "from ocr import extract_text; print(extract_text('akte-bucket','uploads/yourfile.pdf')[:300])"
#
# Full working code is in the blueprint document (Section: PERSON B, "Full code — ocr.py").

import boto3
import pdfplumber
import io
import re

s3 = boto3.client('s3')
textract = boto3.client('textract', region_name='us-east-1')


def _download(bucket, key):
    # TODO: s3.get_object and return Body bytes
    raise NotImplementedError


def _digital(pdf_bytes):
    # TODO: pdfplumber extraction, returns (text, pages_with_text_count)
    raise NotImplementedError


def _scanned(bucket, key):
    # TODO: textract.detect_document_text, returns joined LINE text
    raise NotImplementedError


def _clean(text):
    # TODO: remove noise — page numbers, decorators, short fragments, collapse newlines
    raise NotImplementedError


def extract_text(bucket, key):
    """
    Main entry point called by main_handler.py.
    Tries digital extraction first, falls back to Textract for scanned PDFs.
    Raises ValueError if nothing extracted.
    """
    # TODO: implement as described above
    raise NotImplementedError
