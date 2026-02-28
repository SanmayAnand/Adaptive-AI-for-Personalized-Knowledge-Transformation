# AKTE — Adaptive Knowledge Transformation Engine
### Team 600CR · AWS AI for Bharat Hackathon

---

## What this app does
1. User uploads a PDF on the website
2. AI reads the PDF and generates 5 quiz questions about it
3. User answers the quiz → app detects if they're a beginner / intermediate / expert
4. The whole PDF is rewritten to match that level
5. User downloads the personalized document

---

## Folder structure & who owns what

```
akte-600cr/
│
├── main_handler.py        ← Person A writes this (wires OCR + Transform together)
├── requirements.txt       ← Python packages for the whole backend
│
├── ocr/                   ← Person B works here (PDF → clean text)
│   ├── README.md
│   └── ocr.py
│
├── transform/             ← Person C works here (text → AI rewritten text)
│   ├── README.md
│   └── transform.py
│
├── quiz/                  ← Person D works here (quiz Lambda)
│   ├── README.md
│   └── quiz_handler.py
│
├── frontend/              ← Person D also works here (React website)
│   ├── README.md
│   ├── package.json
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── App.js
│       ├── App.css
│       ├── api.js
│       └── components/
│           ├── Upload.js
│           ├── Quiz.js
│           ├── LevelResult.js
│           └── Download.js
│
└── infra/
    └── README.md          ← Person A follows this to set up AWS
```

---

## Who owns what

| Person | Files | Job |
|--------|-------|-----|
| **A** | `main_handler.py` + `infra/README.md` | Set up all AWS resources. Write the Lambda that calls OCR and Transform. Deploy everything. |
| **B** | `ocr/ocr.py` | Read a PDF from S3 and return clean text. One function: `extract_text(bucket, key)` |
| **C** | `transform/transform.py` | Take clean text + user level → call Bedrock AI → return rewritten text. One function: `rewrite(text, level)` |
| **D** | `quiz/quiz_handler.py` + all of `frontend/` | AI quiz that detects user level. The entire React website. |

---

## The full pipeline (what happens when someone uses the app)

```
User opens website
  ↓
Uploads a PDF  →  akte-upload Lambda saves it to S3
  ↓
App calls akte-quiz Lambda  →  AI generates 5 questions from the PDF
  ↓
User answers quiz  →  score calculated  →  level saved to DynamoDB
  ↓
User clicks "Transform"  →  akte-main Lambda runs:
    → ocr.py reads the PDF → gets clean text
    → transform.py rewrites the text for their level
    → saves result to S3
    → returns a download link
  ↓
User downloads their personalized document
```

---

## AWS services used
- **S3** (`akte-bucket`) — stores uploaded PDFs, outputs, and the website itself
- **DynamoDB** (`akte-users`) — stores each user's detected level
- **Bedrock** (Claude 3 Haiku) — generates quiz questions + rewrites text
- **Textract** — OCR fallback for scanned PDFs
- **Lambda** — 4 serverless functions (no servers to manage)

---

## Day-by-day plan

| Day | Person A | Person B | Person C | Person D |
|-----|----------|----------|----------|----------|
| **Day 1 AM** | Create all AWS resources. Issue keys to B, C, D. | Install packages. Test pdfplumber locally on any PDF. | Set up AWS. Test a Bedrock call. Write the 3 prompts. | Set up React app. Build Upload screen. |
| **Day 1 PM** | Build pdfplumber Lambda Layer. Deploy upload + profile Lambdas. | Write `_digital()` and `_clean()`. Test on 3 PDFs. | Finish all 3 prompts. Test all 3 levels on the same paragraph. | Write quiz_handler.py. Write Quiz screen UI. |
| **Day 2 AM** | Receive ocr.py + transform.py. Write main_handler.py. Deploy akte-main. | Finish ocr.py. Send file to A. | Finish transform.py. Send file to A. | Deploy akte-quiz. Write LevelResult screen. |
| **Day 2 PM** | Share all 4 Lambda URLs in group chat. | Test full pipeline end to end. | Test 3 different PDFs. Tune prompts. | Plug real URLs into api.js. Test the whole app. |
| **Day 3** | Host the React /build folder on S3. Share live URL. | Regression test. Debug any OCR issues. | Final prompt tuning. | npm run build → send /build to A. Fix UI bugs. |

---

## IMPORTANT: Never put AWS keys in any file
Everyone runs `aws configure` on their own laptop. Keys live in `~/.aws/credentials`, not in code.
