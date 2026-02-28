// =============================================================================
// src/api.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: All calls to the backend Lambdas in one place
// =============================================================================
//
// IMPORTANT: Replace the 4 placeholder URLs below once Person A shares them.
// Person A will post the URLs in the group chat after deploying the Lambdas.
//
// =============================================================================

const URLS = {
  upload:    'https://REPLACE_WITH_AKTE_UPLOAD_LAMBDA_URL',    // ← Person A gives you this
  quiz:      'https://REPLACE_WITH_AKTE_QUIZ_LAMBDA_URL',      // ← Person A gives you this
  profile:   'https://REPLACE_WITH_AKTE_PROFILE_LAMBDA_URL',   // ← Person A gives you this
  transform: 'https://REPLACE_WITH_AKTE_MAIN_LAMBDA_URL',      // ← Person A gives you this
};


// ─────────────────────────────────────────────────────────────────────────────
// uploadPDF(file)
// Sends the PDF file to the upload Lambda as base64-encoded bytes.
// Returns: { message: 'uploaded', filename: '...' }
//
// HOW TO IMPLEMENT:
//   const b64 = await new Promise((resolve, reject) => {
//     const reader = new FileReader();
//     reader.onload  = () => resolve(reader.result.split(',')[1]);  // take the base64 part after the comma
//     reader.onerror = reject;
//     reader.readAsDataURL(file);
//   });
//   const response = await fetch(`${URLS.upload}?filename=${encodeURIComponent(file.name)}`, {
//     method: 'POST',
//     body: b64,    // NOTE: no Content-Type header — body is plain base64 string
//   });
//   return response.json();
// ─────────────────────────────────────────────────────────────────────────────
export const uploadPDF = async (file) => {
  // TODO: implement this
};


// ─────────────────────────────────────────────────────────────────────────────
// generateQuiz(filename)
// Asks the quiz Lambda to generate 5 questions from the uploaded PDF.
// Returns: { questions: [ {question, options: {A,B,C}, correct}, ... ] }
//
// HOW TO IMPLEMENT:
//   const response = await fetch(URLS.quiz, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify({ action: 'generate', filename }),
//   });
//   return response.json();
// ─────────────────────────────────────────────────────────────────────────────
export const generateQuiz = async (filename) => {
  // TODO: implement this
};


// ─────────────────────────────────────────────────────────────────────────────
// scoreQuiz(userId, questions, answers)
// Sends the user's answers to the quiz Lambda. Gets back their score and level.
// answers format: { '0': 'A', '1': 'C', '2': 'B', '3': 'A', '4': 'C' }
// Returns: { score: 3, total: 5, level: 'intermediate', message: '...' }
//
// HOW TO IMPLEMENT:
//   const response = await fetch(URLS.quiz, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify({ action: 'score', user_id: userId, questions, answers }),
//   });
//   return response.json();
// ─────────────────────────────────────────────────────────────────────────────
export const scoreQuiz = async (userId, questions, answers) => {
  // TODO: implement this
};


// ─────────────────────────────────────────────────────────────────────────────
// transformDoc(userId, filename)
// Triggers the full pipeline: OCR → AI rewrite → save to S3 → return download link.
// Returns: { download_url: 'https://s3.presigned.url...' }
//
// HOW TO IMPLEMENT:
//   const response = await fetch(URLS.transform, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify({ user_id: userId, filename }),
//   });
//   return response.json();
// ─────────────────────────────────────────────────────────────────────────────
export const transformDoc = async (userId, filename) => {
  // TODO: implement this
};
