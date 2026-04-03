# 🧠 Quiz Module — AKTE

**Lambdas:** `akte-upload` · `akte-quiz` · `akte-profile`
**Runtime:** Python 3.12 · AWS Lambda · Amazon Bedrock

> Part of [AKTE — Adaptive Knowledge Transformation Engine](http://akte-frontend.s3-website-us-east-1.amazonaws.com/) · AWS AI for Bharat Hackathon 2026 · Team 600CR

---

## Overview

This folder contains the three serverless Lambda functions that form the **assessment and profile layer** of AKTE. Together they handle file ingestion, AI-powered quiz generation, adaptive knowledge-level detection, and user profile management.

| File | Lambda | Responsibility |
|------|--------|----------------|
| `upload_handler.py` | `akte-upload` | Generates pre-signed S3 URLs for direct browser-to-S3 file uploads. Enforces whitelist filename sanitisation and validates PDF / DOCX file types. |
| `quiz_handler.py` | `akte-quiz` | Polls extraction readiness, generates MCQs via Amazon Bedrock, scores answers using a two-rule adaptive engine, and persists the user's knowledge level and intent to DynamoDB. |
| `profile_handler.py` | `akte-profile` | Reads a user's assessed level for a specific document session and supports manual level override from the Level Result screen. |

---

## Pipeline Flow

```
User uploads PDF / DOCX
        ↓
akte-upload  →  pre-signed S3 URL  →  file lands in uploads/
        ↓
S3 trigger fires  →  akte-ocr extracts text
        →  saves to extracted/{user_id}/{filename}.txt
        ↓
Frontend polls akte-quiz (check_ready) every 3–5 seconds
        ↓  ready: true
akte-quiz reads extracted text  →  calls Bedrock  →  MCQs returned
        ↓
User answers quiz + self-assessment
        ↓
akte-quiz scores answers  →  level + intent saved to DynamoDB
        ↓
Level Result screen  →  akte-profile  →  optional level override
        ↓
User triggers Transform  →  akte-main rewrites document using level + intent
```

---

## API Reference

All three Lambdas accept a JSON body and return JSON. All responses include `Access-Control-Allow-Origin: *`.

### `akte-upload`

```json
POST { "user_id": "abc123", "filename": "biology notes.pdf" }

200 → {
  "upload_url": "https://...",
  "filename": "biology_notes.pdf",
  "s3_key": "uploads/abc123/biology_notes.pdf",
  "content_type": "application/pdf",
  "expires_in": 300
}

400 → { "error": "Only .pdf, .docx files are accepted" }
400 → { "error": "user_id contains invalid characters" }
```

> ⚠️ Always use the `filename` field from the response in all subsequent calls — the backend sanitises the original filename (e.g. spaces become underscores, special characters are stripped).

---

### `akte-quiz`

**`check_ready`** — poll until text extraction is complete:
```json
POST { "action": "check_ready", "user_id": "abc123", "filename": "biology_notes.pdf" }

200 → { "ready": false }
200 → { "ready": true, "doc_id": "abc123#biology_notes.pdf#20260306120000" }
```

**`generate`** — generate quiz questions via Bedrock:
```json
POST { "action": "generate", "user_id": "abc123", "filename": "biology_notes.pdf" }

200 → {
  "self_questions": [...],
  "mcq_questions": [...],
  "word_count": 842,
  "extraction_note": "ok"
}
422 → { "error": "...", "extraction_note": "unreadable", "word_count": 0 }
429 → { "error": "...", "retry_after_seconds": 45 }
```

**`score`** — score answers and save level to DynamoDB:
```json
POST {
  "action": "score",
  "user_id": "abc123",
  "doc_id": "abc123#biology_notes.pdf#20260306120000",
  "filename": "biology_notes.pdf",
  "mcq_questions": [...],
  "mcq_answers": { "0": "A", "1": "C", "2": "B", "3": "A", "4": "C" },
  "self_answers": { "background": "some", "intent": "studying" },
  "word_count": 842,
  "extraction_note": "ok"
}

200 → { "score": 3, "level": "intermediate", "intent": "studying", "doc_id": "..." }
```

**`history`** — retrieve all document sessions for a user:
```json
POST { "action": "history", "user_id": "abc123" }

200 → { "documents": [ { "doc_id": "...", "level": "...", "filename": "...", ... } ] }
```

---

### `akte-profile`

**`get_level`** — read current assessed level for a document session:
```json
POST {
  "action": "get_level",
  "user_id": "abc123",
  "doc_id": "abc123#biology_notes.pdf#20260306120000"
}

200 → {
  "user_id": "abc123",
  "doc_id": "abc123#biology_notes.pdf#20260306120000",
  "level": "intermediate",
  "filename": "biology_notes.pdf",
  "quiz_score": 3
}
404 → { "error": "No document found for doc_id '...'" }
```

**`set_level`** — manually override the assessed level:
```json
POST {
  "action": "set_level",
  "user_id": "abc123",
  "doc_id": "abc123#biology_notes.pdf#20260306120000",
  "level": "beginner"
}

200 → { "user_id": "...", "doc_id": "...", "level": "beginner", "updated_at": "..." }
400 → { "error": "level must be 'beginner', 'intermediate', or 'expert'" }
404 → { "error": "No document found for doc_id '...'" }
```

---

## Adaptive Scoring Logic

Knowledge level is determined by two signals — MCQ performance and self-reported background — applied in order:

**Rule 1 — Lucky guesser override:**
If background is `none` or `some` AND MCQ score implies `expert`, cap at `intermediate`. With 3-option questions, pure guessing yields ~33% per question. A zero-background user scoring 4–5/5 is statistically more likely guessing than genuinely expert.

**Rule 2 — Boundary nudge:**
At boundary scores (2/5, 4/5 for 5-question sets · 1/3, 2/3 for 3-question sets), if self-reported background maps to a lower level than MCQ implied, nudge down one tier. Never nudges up.

| MCQ Score | Background | Final Level |
|-----------|-----------|-------------|
| 5/5 | deep / working | `expert` |
| 5/5 | none / some | `intermediate` ← Rule 1 |
| 4/5 | deep | `expert` |
| 4/5 | working | `intermediate` ← Rule 2 |
| 4/5 | none / some | `intermediate` ← Rule 1 |
| 3/5 | any | `intermediate` |
| 2/5 | deep / working | `intermediate` |
| 2/5 | none / some | `beginner` ← Rule 2 |
| 0–1/5 | any | `beginner` |

---

## Security

| Feature | Implementation |
|---------|---------------|
| No hardcoded credentials | `boto3` uses the Lambda execution role — no keys in code |
| Filename sanitisation | ASCII-only whitelist `[a-zA-Z0-9_\-\.]` — not a blacklist |
| Atomic rate limiting | DynamoDB `ConditionExpression` on `put_item` — race-condition-proof across parallel Lambda instances; 1 generate call per user per 60 seconds |
| Prompt injection defence | Extracted text wrapped in `<document>` XML tags; system prompt instructs Bedrock to treat content as source material only |
| Input validation | `user_id` and `doc_id` validated against strict regex whitelists before any AWS call |
| Safe DynamoDB writes | `update_item` in `akte-profile` — only patches `level` and `updated_at`, never overwrites the full row |

---

## Local Testing

Configure AWS credentials:

```bash
pip install boto3
aws configure
```

Upload a test file:

```bash
aws s3 cp sample.pdf s3://akte-bucket/uploads/test-user-1/sample.pdf
```

Simulate Lambda calls locally:

```python
import json
from quiz_handler import lambda_handler

# 1. Check extraction readiness
event = {'body': json.dumps({
    'action': 'check_ready',
    'user_id': 'test-user-1',
    'filename': 'sample.pdf'
})}
print(lambda_handler(event, None))

# 2. Generate quiz (only after ready: true)
event = {'body': json.dumps({
    'action': 'generate',
    'user_id': 'test-user-1',
    'filename': 'sample.pdf'
})}
print(lambda_handler(event, None))

# 3. Score answers
qs = [{'question': 'Q?', 'options': {'A': 'Yes', 'B': 'No', 'C': 'Maybe'}, 'correct': 'A'}]
event = {'body': json.dumps({
    'action': 'score',
    'user_id': 'test-user-1',
    'doc_id': 'test-user-1#sample.pdf#20260306120000',
    'filename': 'sample.pdf',
    'mcq_questions': qs,
    'mcq_answers': {'0': 'A'},
    'self_answers': {'background': 'none', 'intent': 'studying'},
    'word_count': 500,
    'extraction_note': 'ok'
})}
print(lambda_handler(event, None))
```

---

## AWS Infrastructure

| Resource | Name | Detail |
|----------|------|--------|
| S3 Bucket | `akte-bucket` | Paths: `uploads/` · `extracted/` · `outputs/` |
| DynamoDB Table | `akte-users` | Partition key: `user_id` (String) · Sort key: `doc_id` (String) |
| Bedrock Model | `anthropic.claude-3-haiku-20240307-v1:0` | Region: `us-east-1` |
| Lambda Role | `akte-lambda-role` | Requires: `PutItem` · `GetItem` · `UpdateItem` · `Query` · S3 read/write · Bedrock `InvokeModel` |

---

## DynamoDB Schema

Each scored document session writes one row:

```
user_id            String   partition key
doc_id             String   sort key — format: user_id#filename#YYYYMMDDHHMMSS
filename           String   sanitised filename
level              String   beginner / intermediate / expert
quiz_score         Number   0–5
intent             String   studying / applying / explaining / exploring
self_answers       Map      full self-assessment response
word_count         Number   word count of extracted text
extraction_note    String   ok / too_short / unreadable
transform_status   String   pending / complete / failed
s3_original_key    String   uploads/{user_id}/{filename}
s3_extracted_key   String   extracted/{user_id}/{filename}.txt
created_at         String   ISO 8601 timestamp
updated_at         String   ISO 8601 timestamp
```

> ⚠️ The `akte-ocr` and `akte-main` Lambdas must use `update_item` — not `put_item` — when writing back to this table. `put_item` replaces the entire row and will overwrite quiz results, scores, and intent.

---

## File Structure

```
quiz/
├── upload_handler.py    # akte-upload  — file ingestion
├── quiz_handler.py      # akte-quiz   — assessment pipeline
├── profile_handler.py   # akte-profile — level management
└── README.md
```

---

*AKTE — Adaptive Knowledge Transformation Engine · AWS AI for Bharat Hackathon 2026 · Team 600CR*
- SHAILJA MISHRA