# backend/lambda-main/

## Who owns this
Person A writes `main_handler.py`.
Person B writes `ocr.py` and sends it to A.
Person C writes `transform.py` and sends it to A.
Person A zips all three together and deploys as `akte-main`.

## Files in this folder
```
lambda-main/
├── main_handler.py       # Person A — orchestrator (wire OCR → transform → S3)
├── ocr.py                # Person B — PDF text extraction (place here when received)
└── transform.py          # Person C — Bedrock rewriting (place here when received)
```

## How to deploy (Person A)
See `../../scripts/zip_main.sh` — it zips all three files and produces `akte_main.zip`.
Upload to akte-main Lambda. Add pdfplumber-layer.

## Lambda settings
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 60 seconds
- Role: akte-lambda-role
- Layer: pdfplumber-layer (required — ocr.py imports pdfplumber)
