// =============================================================================
// src/components/Quiz.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: Screen 2 — shows 5 questions, user picks A/B/C for each
// =============================================================================
//
// THIS IS THE MOST IMPORTANT UI SCREEN. Make it look great.
// The quiz is what makes this project stand out from every other submission.
//
// PROPS:
//   userId    — random user ID from App.js
//   filename  — shown in subtitle: "These questions are about {filename}"
//   questions — array of 5 objects: { question, options: {A,B,C}, correct }
//   onDone(result) — call after scoring. result = { score, total, level, message }
//
// STATE:
//   answers  — object like { '0': 'A', '1': 'C', '2': 'B', '3': 'A', '4': 'C' }
//              starts as {} and fills up as user clicks radio buttons
//   loading  — boolean
//   error    — string
//
// COMPUTED (derive this from state, not store it):
//   allAnswered = questions.every((_, i) => answers[String(i)] !== undefined)
//
// WHAT HAPPENS WHEN "Submit Answers" IS CLICKED:
//   1. If !allAnswered → setError('Please answer all 5 questions.') and return
//   2. setLoading(true)
//   3. result = await scoreQuiz(userId, questions, answers)
//   4. onDone(result)   ← switches to Level Result screen
//   Catch: setError('Error: ' + e.message)  then setLoading(false)
//
// JSX TO BUILD:
//   <div className="screen">
//     <h1>Knowledge Check</h1>
//     <p className="sub">
//       These 5 questions are about <strong>{filename}</strong>.
//       Your answers help us personalise the document for your level.
//     </p>
//
//     {questions.map((q, i) => (
//       <div key={i} className="card question-card">
//         <p className="qnum">Question {i + 1} of {questions.length}</p>
//         <p className="qtext">{q.question}</p>
//
//         {Object.entries(q.options).map(([key, text]) => (
//           <label key={key} className={`option ${answers[String(i)] === key ? 'selected' : ''}`}>
//             <input
//               type="radio"
//               name={`q${i}`}
//               value={key}
//               checked={answers[String(i)] === key}
//               onChange={() => setAnswers({ ...answers, [String(i)]: key })}
//             />
//             <span className="opt-key">{key}.</span> {text}
//           </label>
//         ))}
//       </div>
//     ))}
//
//     {error && <p className="error">{error}</p>}
//     <button className="btn" onClick={submit} disabled={loading || !allAnswered}>
//       {loading ? 'Submitting...' : 'Submit Answers'}
//     </button>
//   </div>
//
// =============================================================================

import { useState } from 'react';
import { scoreQuiz } from '../api';

export default function Quiz({ userId, filename, questions, onDone }) {
  // TODO: implement this — full guide above
}
