// =============================================================================
// src/components/Upload.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: Screen 1 — user picks a PDF and clicks "Upload & Start Quiz"
// =============================================================================
//
// PROPS:
//   userId  — the random user ID from App.js (you don't use it here, but pass it down eventually)
//   onDone(filename, questions) — call this when upload + quiz generation both succeed.
//                                  App.js will switch to the Quiz screen.
//
// STATE:
//   file     — the File object the user selected (null until they pick one)
//   status   — a string message to show below the button (e.g. "Uploading...")
//   loading  — boolean, true while waiting for API calls to finish
//
// WHAT HAPPENS WHEN "Upload & Start Quiz" IS CLICKED:
//   1. If no file selected → setStatus('Please select a PDF first.')  and return
//   2. setLoading(true)
//   3. setStatus('Uploading PDF...')
//   4. await uploadPDF(file)
//   5. setStatus('AI is reading your document and generating quiz questions...')
//   6. data = await generateQuiz(file.name)
//   7. If data.questions is missing → throw error
//   8. onDone(file.name, data.questions)   ← this switches to the Quiz screen
//   Catch: setStatus('Error: ' + error.message)  then setLoading(false)
//
// JSX TO BUILD:
//   <div className="screen">
//     <h1>Upload Your Document</h1>
//     <p className="sub">AKTE will read your PDF, quiz you on it, and personalise the content to your level.</p>
//     <div className="card">
//       <label className="label">Select a PDF</label>
//       <input type="file" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
//       {file && <p className="fname">{file.name} — {(file.size / 1024).toFixed(0)} KB</p>}
//     </div>
//     <button className="btn" onClick={handle} disabled={loading}>
//       {loading ? 'Processing...' : 'Upload & Start Quiz'}
//     </button>
//     {status && <p className="status">{status}</p>}
//   </div>
//
// =============================================================================

import { useState } from 'react';
import { uploadPDF, generateQuiz } from '../api';

export default function Upload({ userId, onDone }) {
  // TODO: implement this — full guide above
}
