// =============================================================================
// src/components/LevelResult.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: Screen 3 — shows score and detected level, lets user override,
//               has the "Transform Document" button
// =============================================================================
//
// PROPS:
//   result        — { score, total, level, message } from the quiz score step
//   userId        — random user ID
//   filename      — the PDF filename
//   onTransform(data) — call after transform succeeds. data = { download_url }
//
// STATE:
//   selectedLevel  — starts as result.level, user can change it with override buttons
//   loading        — boolean
//   error          — string
//
// LEVEL DESCRIPTIONS (show one based on selectedLevel):
//   beginner:     "We'll explain everything step by step with examples and analogies."
//   intermediate: "We'll keep the technical detail but trim the obvious basics."
//   expert:       "We'll condense everything down to the key insights only."
//
// WHAT HAPPENS WHEN "Transform Document" IS CLICKED:
//   1. setLoading(true)
//   2. (Optional but good) POST to profile Lambda to save the selectedLevel override
//        await fetch(PROFILE_URL, { method: 'POST', body: { user_id, level: selectedLevel } })
//        But keep this simple — if it fails, don't crash. The quiz already saved a level.
//   3. data = await transformDoc(userId, filename)
//   4. onTransform(data)   ← switches to Download screen
//   Catch: setError('Error: ' + e.message)  then setLoading(false)
//
// JSX TO BUILD:
//   <div className="screen">
//     <h1>Your Knowledge Level</h1>
//     <div className="card level-card">
//       <div className="level-badge">{result.level.toUpperCase()}</div>
//       <div className="score">Score: {result.score} / {result.total}</div>
//       <div className="level-desc">{description for result.level}</div>
//     </div>
//
//     <p>Not quite right? Override your level:</p>
//     <div className="override-row">
//       {['beginner', 'intermediate', 'expert'].map(lvl => (
//         <button key={lvl}
//           className={`btn-sec ${selectedLevel === lvl ? 'active' : ''}`}
//           onClick={() => setSelectedLevel(lvl)}>
//           {lvl}
//         </button>
//       ))}
//     </div>
//
//     {error && <p className="error">{error}</p>}
//     <button className="btn" onClick={handle} disabled={loading}>
//       {loading ? 'Transforming...' : `Transform as ${selectedLevel.toUpperCase()}`}
//     </button>
//   </div>
//
// =============================================================================

import { useState } from 'react';
import { transformDoc } from '../api';

export default function LevelResult({ result, userId, filename, onTransform }) {
  // TODO: implement this — full guide above
}
