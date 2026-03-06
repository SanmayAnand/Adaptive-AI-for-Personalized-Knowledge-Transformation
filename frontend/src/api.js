// =============================================================================
// src/api.js  —  all Lambda calls live here
//
// SETUP: Replace these URLs once Person A deploys and shares Lambda Function URLs
// Person A will message you something like:
//   akte-upload:  https://xxxx.lambda-url.us-east-1.on.aws/
//   akte-quiz:    https://yyyy.lambda-url.us-east-1.on.aws/
//   akte-main:    https://zzzz.lambda-url.us-east-1.on.aws/
// =============================================================================

const LAMBDA_URLS = {
  upload:  process.env.REACT_APP_UPLOAD_URL  || 'https://gkflvib3kj6fcsf7jdgoucg66m0lsrsp.lambda-url.us-east-1.on.aws/',
  quiz:    process.env.REACT_APP_QUIZ_URL    || 'https://2z6as6xrcozizucl2knynd2y7i0xmgao.lambda-url.us-east-1.on.aws/',
  main:    process.env.REACT_APP_MAIN_URL    || 'https://qcjoawokvwqsnm7xttf6mxt3oa0dbxxp.lambda-url.us-east-1.on.aws/',
};

// ── Helper ────────────────────────────────────────────────────────────────────
async function post(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// =============================================================================
// STEP 1 — Get a pre-signed upload URL
// upload_handler.py returns { upload_url, filename (sanitised), s3_key, content_type }
// IMPORTANT: always use the returned `filename` (sanitised) in all future calls
// =============================================================================
export async function getUploadUrl(userId, rawFilename) {
  return post(LAMBDA_URLS.upload, { user_id: userId, filename: rawFilename });
}

// =============================================================================
// STEP 2 — PUT file directly to S3 using the pre-signed URL
// This bypasses Lambda — file goes straight from browser to S3.
// Returns nothing on success (S3 returns 200 with empty body).
// =============================================================================
export async function uploadFileToS3(presignedUrl, file, contentType) {
  const res = await fetch(presignedUrl, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,                // raw bytes — NOT base64
  });
  if (!res.ok) throw new Error(`S3 upload failed: HTTP ${res.status}`);
}

// =============================================================================
// STEP 3 — Poll until Person B's OCR extraction is done
// quiz_handler action='check_ready' — returns { ready: false } or { ready: true, doc_id }
// =============================================================================
export async function checkReady(userId, filename) {
  return post(LAMBDA_URLS.quiz, { action: 'check_ready', user_id: userId, filename });
}

// Poll with interval. Resolves when ready, rejects after maxAttempts.
export async function pollUntilReady(userId, filename, onProgress, intervalMs = 3000, maxAttempts = 40) {
  for (let i = 0; i < maxAttempts; i++) {
    const result = await checkReady(userId, filename);
    if (result.ready) return result;           // { ready: true, doc_id: "..." }
    if (onProgress) onProgress(i, maxAttempts);
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error('OCR extraction timed out. Please try again.');
}

// =============================================================================
// STEP 4 — Generate quiz questions about the document
// quiz_handler action='generate' — returns { self_questions, mcq_questions, word_count, extraction_note }
// =============================================================================
export async function generateQuiz(userId, filename) {
  return post(LAMBDA_URLS.quiz, { action: 'generate', user_id: userId, filename });
}

// =============================================================================
// STEP 5 — Score the quiz and save level to DynamoDB
// quiz_handler action='score'
// Returns { score, level, intent, doc_id }
// =============================================================================
export async function scoreQuiz(userId, docId, filename, mcqQuestions, mcqAnswers, selfAnswers, wordCount, extractionNote) {
  return post(LAMBDA_URLS.quiz, {
    action:          'score',
    user_id:         userId,
    doc_id:          docId,
    filename:        filename,
    mcq_questions:   mcqQuestions,
    mcq_answers:     mcqAnswers,
    self_answers:    selfAnswers,
    word_count:      wordCount,
    extraction_note: extractionNote,
  });
}

// =============================================================================
// STEP 6 — Transform the document
// main_handler.py — calls transform.run() which calls ocr then AI rewriting
// Returns { download_url, level, intent, annotations, s3_key }
// =============================================================================
export async function transformDocument(userId, filename, docId) {
  return post(LAMBDA_URLS.main, { user_id: userId, filename, doc_id: docId });
}

// =============================================================================
// UTIL — Fetch the text content of a pre-signed URL for the learning view
// =============================================================================
export async function fetchDocumentText(presignedUrl) {
  const res = await fetch(presignedUrl);
  if (!res.ok) throw new Error(`Failed to fetch document: HTTP ${res.status}`);
  return res.text();
}