# AKTE Architecture Notes

## Data Flow Diagram
```
Browser (React SPA hosted on S3)
  │
  ├── Upload PDF ──────────────────────→ akte-upload Lambda
  │                                         └── S3: uploads/{filename}
  │
  ├── Generate Quiz ──────────────────→ akte-quiz Lambda (action: generate)
  │                                         ├── S3: read uploads/{filename} (pdfplumber, first 5 pages)
  │                                         └── Bedrock Claude 3 Haiku → 5 questions JSON
  │
  ├── Submit Answers ─────────────────→ akte-quiz Lambda (action: score)
  │                                         └── DynamoDB: akte-users ← {user_id, level, quiz_score}
  │
  ├── (optional) Override Level ───────→ akte-profile Lambda (POST)
  │                                         └── DynamoDB: akte-users ← {user_id, level}
  │
  └── Transform Document ─────────────→ akte-main Lambda
                                            ├── DynamoDB: akte-users → get user level
                                            ├── ocr.py: S3 → pdfplumber or Textract → clean text
                                            ├── transform.py: Bedrock → rewritten text (chunked)
                                            ├── S3: outputs/{user_id}_{filename}.txt
                                            └── pre-signed URL (1hr) → browser downloads
```

## AWS Resources Summary
| Resource | Name | Config |
|----------|------|--------|
| S3 Bucket | akte-bucket | us-east-1; folders: uploads/, outputs/, website/ |
| DynamoDB | akte-users | PK: user_id (String); On-demand |
| Lambda 1 | akte-main | Python 3.11, 512MB, 60s, pdfplumber-layer |
| Lambda 2 | akte-upload | Python 3.11, 512MB, 60s |
| Lambda 3 | akte-quiz | Python 3.11, 512MB, 60s, pdfplumber-layer |
| Lambda 4 | akte-profile | Python 3.11, 512MB, 60s |
| Bedrock | claude-3-haiku | us-east-1, must be enabled before Day 1 |
| IAM Role | akte-lambda-role | S3+DynamoDB+Bedrock+Textract full access |

## DynamoDB Schema (akte-users)
```
{
  "user_id":    "user_abc123de",  // PK — random string from frontend
  "level":      "intermediate",   // beginner | intermediate | expert
  "quiz_score": 3,                // 0-5
  "updated_at": "2024-01-15T10:30:00"  // ISO UTC
}
```

## Key Design Decisions
1. **No API Gateway** — Lambda Function URLs used directly. Simpler, free, supports CORS.
2. **No login** — user_id is a random string generated client-side. Enough for a hackathon demo.
3. **Bedrock chunking** — transform.py splits long documents into ~400-word chunks so they fit within Bedrock's context window per call.
4. **Textract fallback** — ocr.py tries pdfplumber first (fast, free) and falls back to Textract (costs ~$0.0015/page) only for scanned PDFs.
5. **Correct answers in generate response** — for hackathon simplicity, quiz_handler returns correct answers in the generate response. The frontend holds them and sends them back during scoring. This is fine for a demo.
