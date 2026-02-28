# Day-by-Day Handoff Timeline

## Day 1 AM

| Person | Task |
|--------|------|
| **A** | Creates AWS: S3 bucket, DynamoDB table, IAM role, Bedrock model access. Issues keys to B, C, D. |
| **B** | Installs pdfplumber. Runs `aws configure`. Tests pdfplumber on a local PDF. |
| **C** | Runs `aws configure`. Tests Bedrock call in console playground. Writes `PROMPTS` dict first. |
| **D** | Runs `aws configure`. Sets up React app. Builds Upload screen with fake data. |

## Day 1 PM

| Person | Task |
|--------|------|
| **A** | Builds pdfplumber Lambda Layer. Deploys `akte-upload` and `akte-profile` (Person D's files). |
| **B** | Writes `_digital()` and `_clean()` functions. Tests on 2–3 local PDFs. |
| **C** | Writes all 3 prompts. Tests `rewrite()` on same paragraph for all 3 levels. Compares output. |
| **D** | Writes `quiz_handler.py` locally. Tests `_generate_questions()` against a real Bedrock call. Writes Quiz screen UI. |

## Day 2 AM

| Person | Task |
|--------|------|
| **A** | Receives `ocr.py` (B) + `transform.py` (C). Writes `main_handler.py`. Zips all 3 + deploys `akte-main`. |
| **B** | Finishes `ocr.py`, tests `extract_text()` end-to-end with S3. Sends `ocr.py` to A. |
| **C** | Finishes `transform.py`. Sends to A. |
| **D** | Finishes `quiz_handler.py`. Deploys `akte-quiz`. Writes LevelResult screen. |

## Day 2 PM

| Person | Task |
|--------|------|
| **A** | All 4 Lambdas deployed. Shares all 4 URLs in group chat. |
| **B** | End-to-end test: upload PDF → call main Lambda → download output. Check quality. |
| **C** | Tests full pipeline with 3 different PDFs. Adjusts prompts if outputs aren't good enough. |
| **D** | Plugs real URLs into `api.js`. Tests full 4-screen flow in browser. |

## Day 3

| Person | Task |
|--------|------|
| **A** | Hosts React `/build` on S3. Final live URL shared with team. |
| **B** | Regression test after any prompt changes. Helps debug if OCR fails on scanned PDFs. |
| **C** | Final prompt tuning based on real test results. |
| **D** | `npm run build`. Sends `/build` to A. Fixes any UI bugs after live testing. |

---

## File Handoff Summary
- Person B → Person A: `ocr.py`
- Person C → Person A: `transform.py`
- Person D → Person A: `upload_handler.py`, `quiz_handler.py`, `profile_handler.py`, React `/build` folder
- Person A: zips all backend files, deploys, hosts frontend, shares all URLs
