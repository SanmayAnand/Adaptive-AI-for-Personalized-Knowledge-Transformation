# =============================================================================
# ocr/ocr.py
# WHO WRITES THIS: Person B
# WHAT THIS IS: Reads a PDF from S3 and returns clean plain text
# =============================================================================
#
# YOUR ONE JOB:
#   Write the function extract_text(bucket, key) → string
#   Person A's main_handler.py calls: text = ocr.extract_text('akte-bucket', 'uploads/file.pdf')
#   You return a clean string. That's the entire contract.
#
# THE STRATEGY (2 methods, try in order):
#
#   Method 1 — pdfplumber (for normal text-based PDFs)
#     - Most PDFs have actual text embedded. pdfplumber extracts it directly.
#     - Fast and free.
#
#   Method 2 — AWS Textract (fallback for scanned PDFs)
#     - Scanned PDFs are just images. pdfplumber returns nothing.
#     - If pdfplumber gets less than 150 characters, switch to Textract.
#     - Textract does real OCR on the image. Costs ~$0.0015/page.
#
# INSTALL:
#   pip install pdfplumber boto3
#
# =============================================================================

import boto3
import pdfplumber
import io
import re

s3       = boto3.client('s3')
textract = boto3.client('textract', region_name='us-east-1')


def _download(bucket, key):
    """
    Download the PDF from S3 and return the raw bytes.

    HOW TO IMPLEMENT:
      response = s3.get_object(Bucket=bucket, Key=key)
      return response['Body'].read()
    """
    # TODO: implement this
    pass


def _digital(pdf_bytes):
    """
    Try to extract text from a text-based PDF using pdfplumber.
    Returns a tuple: (text_string, number_of_pages_that_had_text)

    If the PDF is scanned (images only), pdfplumber returns nothing,
    so pages_with_text will be 0.

    HOW TO IMPLEMENT:
      text = ''
      pages_with_text = 0
      with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
          for page in pdf.pages:
              t = page.extract_text()
              if t and len(t.strip()) > 20:
                  text += t + '\n'
                  pages_with_text += 1
      return text, pages_with_text
    """
    # TODO: implement this
    pass


def _scanned(bucket, key):
    """
    Use AWS Textract to OCR a scanned/image PDF directly from S3.
    Returns the extracted text as a string.

    HOW TO IMPLEMENT:
      response = textract.detect_document_text(
          Document={'S3Object': {'Bucket': bucket, 'Name': key}}
      )
      # Textract returns blocks. We only want LINE blocks (not WORD blocks).
      lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
      return '\n'.join(lines)
    """
    # TODO: implement this
    pass


def _clean(text):
    """
    Remove noise from the extracted text.
    Returns a cleaner version of the text.

    WHAT TO REMOVE:
      - Blank lines
      - Lines that are just a page number (e.g. "1", "23", "142")
      - Lines that are just decorative (e.g. "---", "====", ".....")
      - Very short fragments under 4 words (unless they look like a heading)
      - More than 2 consecutive blank lines → collapse to 1 blank line

    HOW TO IMPLEMENT:
      cleaned = []
      for line in text.split('\n'):
          s = line.strip()
          if not s:
              continue                              # skip blank lines
          if re.fullmatch(r'\d{1,4}', s):
              continue                              # skip lone page numbers like "42"
          if re.fullmatch(r'[-._=]{3,}', s):
              continue                              # skip decorative lines like "------"
          if len(s.split()) < 4:
              if not (s.istitle() or s.isupper()):  # keep short lines that look like headings
                  continue
          cleaned.append(s)
      # Collapse 3+ blank lines into 1
      return re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned)).strip()
    """
    # TODO: implement this
    pass


def extract_text(bucket, key):
    """
    MAIN FUNCTION — this is the only function Person A calls.

    Takes a PDF from S3 and returns clean extracted text.
    Tries pdfplumber first. Falls back to Textract if the PDF is scanned.
    Raises ValueError if no text could be extracted at all.

    HOW TO IMPLEMENT:
      print(f'[OCR] extracting: {key}')

      # Step 1: Download the PDF
      pdf_bytes = _download(bucket, key)

      # Step 2: Try text-based extraction
      text, pages_found = _digital(pdf_bytes)
      print(f'[OCR] pdfplumber found text on {pages_found} pages')

      # Step 3: If pdfplumber got nothing, use Textract
      if pages_found == 0 or len(text.strip()) < 150:
          print('[OCR] falling back to Textract')
          text = _scanned(bucket, key)

      # Step 4: Clean the text
      text = _clean(text)

      # Step 5: Error if still nothing
      if not text:
          raise ValueError(f'No extractable text found in {key}')

      print(f'[OCR] done: {len(text)} characters extracted')
      return text
    """
    # TODO: implement this
    pass
