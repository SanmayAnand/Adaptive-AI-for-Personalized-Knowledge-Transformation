#!/bin/bash
# tests/backend/e2e_curl_tests.sh
# Copy-paste commands for testing after Day 2 (all Lambda URLs shared by Person A)
#
# Fill in the 4 Lambda URLs before running.
# Run individual sections as needed.

UPLOAD_URL="https://YOUR_UPLOAD_LAMBDA_URL"
QUIZ_URL="https://YOUR_QUIZ_LAMBDA_URL"
PROFILE_URL="https://YOUR_PROFILE_LAMBDA_URL"
MAIN_URL="https://YOUR_MAIN_LAMBDA_URL"
TEST_PDF="test.pdf"   # put a test PDF in this directory

# ─────────────────────────────────────────────────────
# 1. Upload a test PDF to S3 (via AWS CLI)
# ─────────────────────────────────────────────────────
echo "=== Step 1: Upload test PDF to S3 ==="
aws s3 cp $TEST_PDF s3://akte-bucket/uploads/$TEST_PDF

# ─────────────────────────────────────────────────────
# 2. Test OCR locally (Person B)
# ─────────────────────────────────────────────────────
echo "=== Step 2: Test OCR ==="
python3 -c "
from backend.lambda_main.ocr import extract_text
print(extract_text('akte-bucket', 'uploads/$TEST_PDF')[:300])
"

# ─────────────────────────────────────────────────────
# 3. Test quiz generate (Person D)
# ─────────────────────────────────────────────────────
echo "=== Step 3: Test quiz generate ==="
curl -s -X POST $QUIZ_URL \
  -H 'Content-Type: application/json' \
  -d "{\"action\":\"generate\",\"filename\":\"$TEST_PDF\"}" | python3 -m json.tool

# ─────────────────────────────────────────────────────
# 4. Test quiz score (Person D) — paste questions from step 3
# ─────────────────────────────────────────────────────
echo "=== Step 4: Test quiz score ==="
curl -s -X POST $QUIZ_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "score",
    "user_id": "test-u1",
    "questions": [
      {"question": "Test?", "options": {"A": "Yes", "B": "No", "C": "Maybe"}, "correct": "A"}
    ],
    "answers": {"0": "A"}
  }' | python3 -m json.tool

# ─────────────────────────────────────────────────────
# 5. Test full pipeline (everyone, end-to-end)
# ─────────────────────────────────────────────────────
echo "=== Step 5: Full pipeline test ==="
curl -s -X POST $MAIN_URL \
  -H 'Content-Type: application/json' \
  -d "{\"user_id\":\"test-u1\",\"filename\":\"$TEST_PDF\"}" | python3 -m json.tool

# Expected response: { "download_url": "https://akte-bucket.s3..." }
# Paste the download_url into a browser to download the rewritten document
