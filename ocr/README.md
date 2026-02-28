# OCR — PDF to Clean Text
### Person B works in this folder

---

## Your job in one sentence
Write one Python function: `extract_text(bucket, key)` that downloads a PDF from S3 and returns clean text as a string.

## Who calls your function
`main_handler.py` (Person A's file) calls it like this:
```python
text = ocr.extract_text('akte-bucket', 'uploads/myfile.pdf')
```
That's it. You return a string. Person A handles the rest.

---

## Setup on your laptop

```
pip install pdfplumber boto3
aws configure    ← run this with the keys Person A sent you
```

---

## How to test your code locally

1. Upload a test PDF to S3:
```
aws s3 cp any_pdf_you_have.pdf s3://akte-bucket/uploads/test.pdf
```

2. Test your function:
```python
from ocr import extract_text
text = extract_text('akte-bucket', 'uploads/test.pdf')
print(f"Got {len(text)} characters")
print(text[:500])
```

Good output: readable paragraphs, no random page numbers.
Bad output: empty string, or garbage symbols.

---

## When you're done
Send `ocr.py` to Person A. They put it alongside `main_handler.py` and deploy together.
**The function name must stay exactly `extract_text(bucket, key)` — Person A imports it by that name.**
