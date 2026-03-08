# AKTE — Adaptive Knowledge Transformation Engine

> **AWS AI for Bharat Hackathon 2025**
> Your document, rewritten for you.

AKTE takes any PDF or Word document and rewrites it to match your exact knowledge level — with highlights, inline notes, clickable term definitions, and a study game built from your document's own content.

---

## What It Does

Most learning tools summarise your content. AKTE personalises it. Upload a research paper, policy document, or textbook chapter and AKTE will:

1. **Read your document** — extracts full text via AWS Textract with OCR support
2. **Quiz you on it** — generates 5 questions from your document's actual content to assess your level
3. **Rewrite it for you** — Claude Haiku rewrites the full document at beginner, intermediate, or expert level
4. **Give you a rich reading environment** — highlights, inline notes, clickable term definitions, and a toggle back to the original
5. **Let you play to learn** — flashcard game built entirely from your document

---

## Demo

*(Link to demo video)*

---

## Architecture

```
                        ┌─────────────────┐
                        │   React Frontend │
                        │  (S3 Static Host)│
                        └────────┬────────┘
                                 │ Lambda URLs
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
   ┌──────▼──────┐      ┌───────▼───────┐     ┌────────▼───────┐
   │ akte-upload │      │  akte-quiz    │     │   akte-main    │
   │   Lambda    │      │   Lambda      │     │    Lambda      │
   └──────┬──────┘      └───────┬───────┘     └────────┬───────┘
          │                     │                       │
          │ presigned URL        │ Nova Lite             │ Claude Haiku 3.5
          ▼                     ▼                       ▼
   ┌─────────────┐      ┌──────────────┐      ┌────────────────┐
   │     S3      │      │   DynamoDB   │      │    Bedrock     │
   │  (uploads)  │      │  akte-users  │      │   (Bedrock)    │
   └──────┬──────┘      └──────────────┘      └────────────────┘
          │ S3 trigger
          ▼
   ┌─────────────┐
   │  akte-ocr   │
   │   Lambda    │
   │  (Textract) │
   └─────────────┘
```

### AWS Services Used

| Service | Purpose |
|---|---|
| **S3** | Document storage, extracted text, transformed output, frontend hosting |
| **Lambda** | All backend logic — upload, OCR, quiz, transform, profile |
| **DynamoDB** | User knowledge level persistence |
| **Textract** | OCR — extracts text from PDFs and scanned documents |
| **Bedrock (Claude Haiku 3.5)** | Document rewriting and annotation generation |
| **Bedrock (Amazon Nova Lite)** | Quiz question generation (cost-optimised) |

---

## Features

### 📄 Smart Document Ingestion
- Upload PDF or DOCX via pre-signed S3 URL
- S3-triggered Lambda runs AWS Textract OCR automatically
- Supports scanned PDFs, not just digital text

### 🧠 Adaptive Level Detection
- Quiz questions generated directly from your document (not generic)
- Self-assessment for depth of understanding
- Levels: Beginner · Intermediate · Expert

### ✍️ AI-Powered Rewriting
- Full document rewritten by Claude Haiku 3.5 via Amazon Bedrock
- Jargon simplified or expanded based on your level
- 8 annotated terms per document with popup explanations

### 📚 Rich Reading Environment
- **Highlight** text in yellow, blue, or pink — saved across sessions
- **Inline notes** anchored to any paragraph
- **Toggle** between original and personalised version at any time
- **Clickable terms** — underlined key terms show a 2-sentence explanation
- Reading progress bar

### 🎮 Study Game
- Flashcard game built from your document's content
- Tests active recall, not passive reading
- Returns you directly back to your reading position

---

## Project Structure

```
AKTE/
├── frontend/                  # React app
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.svg
│   │   └── playing.html       # Study game (standalone page)
│   └── src/
│       ├── components/
│       │   ├── Upload.js      # Landing + file upload
│       │   ├── Quiz.js        # Level detection quiz
│       │   ├── LevelResult.js # Level reveal + transform trigger
│       │   ├── StudyView.js   # Main reading environment
│       │   ├── StudyGame.js   # Flashcard game
│       │   ├── Sidebar.js     # Document history
│       │   └── Download.js    # PDF export
│       ├── styles/            # Per-component CSS
│       └── api.js             # All Lambda calls
│
├── ocr/
│   ├── ocr_lambda.py          # S3-triggered OCR Lambda
│   └── ocr.py                 # Textract extraction logic
│
├── quiz/
│   ├── quiz_handler.py        # Quiz generation + scoring
│   ├── upload_handler.py      # Pre-signed URL generation
│   └── profile_handler.py     # User level read/write
│
└── main_handler.py            # Transform orchestration (Bedrock)
```

---

## Lambda Functions

| Function | Trigger | Description |
|---|---|---|
| `akte-upload` | HTTP POST | Generates pre-signed S3 URL for direct upload |
| `akte-ocr` | S3 PUT event | Runs Textract on uploaded file, saves extracted text |
| `akte-quiz` | HTTP POST | Generates MCQ questions; scores answers; saves level to DynamoDB |
| `akte-main` | HTTP POST | Orchestrates Bedrock rewrite + annotation generation |
| `akte-profile` | HTTP GET/POST | Reads/writes user knowledge level overrides |

---

## Setup & Deployment

### Prerequisites
- AWS account with access to Bedrock (Claude Haiku 3.5, Amazon Nova Lite)
- Node.js 18+ and npm
- AWS CLI configured

### Environment Variables (all Lambdas)
```
BUCKET_NAME=your-s3-bucket
TABLE_NAME=akte-users
AWS_DEFAULT_REGION=us-east-1
```

### Frontend Environment (`frontend/.env.local`)
```
REACT_APP_UPLOAD_URL=https://YOUR_UPLOAD_LAMBDA_URL/
REACT_APP_QUIZ_URL=https://YOUR_QUIZ_LAMBDA_URL/
REACT_APP_MAIN_URL=https://YOUR_MAIN_LAMBDA_URL/
REACT_APP_PROFILE_URL=https://YOUR_PROFILE_LAMBDA_URL/
```

### Deploy Frontend
```bash
cd frontend
npm install
npm run build
aws s3 sync build/ s3://YOUR-FRONTEND-BUCKET --delete
```

### Lambda Layer (for pdfplumber + python-docx)
```bash
mkdir python
pip install pdfplumber python-docx cryptography \
  -t python/ \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11
zip -r pdfplumber-layer.zip python/
aws s3 cp pdfplumber-layer.zip s3://YOUR-BUCKET/layers/pdfplumber-layer.zip
```

### IAM Permissions (attach to all Lambda roles)
- `AmazonS3FullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonBedrockFullAccess`
- `AmazonTextractFullAccess`

---

## AI Models

| Model | Used For | Why |
|---|---|---|
| `anthropic.claude-haiku-3-5-20251001-v1:0` | Document rewriting + annotations | Fast, high quality, cost-effective for long documents |
| `amazon.nova-lite-v1:0` | Quiz generation | Cheaper for structured MCQ output |

---

## Team

Built for the **AWS AI for Bharat Hackathon 2025** by the team:

Shailja Mishra
Sanmay Anand
Hriday Jadhav
Soumadip Patra

---

## License

MIT