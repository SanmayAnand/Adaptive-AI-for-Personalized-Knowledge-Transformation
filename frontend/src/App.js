// =============================================================================
// src/App.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: The root component. Controls which screen is shown.
// =============================================================================
//
// USER_ID:
//   We don't have a login system. Instead, generate a random ID once when the
//   app loads, and use it for all API calls. This ties together the quiz score
//   and the transform request for the same "session".
//   const USER_ID = 'user_' + Math.random().toString(36).slice(2, 10);
//   Put this OUTSIDE the component (at module level) so it doesn't regenerate on re-renders.
//
// STATE (4 pieces):
//   page:          'upload' | 'quiz' | 'level' | 'download'   — which screen to show
//   filename:      string | null    — the PDF filename, needed by quiz + transform
//   questions:     array            — the 5 question objects from generate step
//   quizResult:    object | null    — { score, total, level, message }
//   downloadData:  object | null    — { download_url }
//
// LAYOUT:
//   <nav> bar at top — shows "AKTE" logo and subtitle
//   Progress indicator — 4 steps: Upload → Quiz → Level → Transform
//     The active step matches the current page.
//   Then render the correct screen component based on `page`.
//
// SCREEN TRANSITIONS:
//   <Upload onDone={(fname, qs) => { setFilename(fname); setQuestions(qs); setPage('quiz'); }} />
//   <Quiz   onDone={(result)    => { setQuizResult(result); setPage('level'); }} />
//   <LevelResult onTransform={(data) => { setDownloadData(data); setPage('download'); }} />
//   <Download    onReset={()   => { setPage('upload'); setFilename(null); }} />
//
// HOW TO IMPLEMENT:
//   import { useState } from 'react';
//   import Upload      from './components/Upload';
//   import Quiz        from './components/Quiz';
//   import LevelResult from './components/LevelResult';
//   import Download    from './components/Download';
//   import './App.css';
//
//   const USER_ID = 'user_' + Math.random().toString(36).slice(2, 10);
//
//   export default function App() {
//     const [page, setPage]               = useState('upload');
//     const [filename, setFilename]       = useState(null);
//     const [questions, setQuestions]     = useState([]);
//     const [quizResult, setQuizResult]   = useState(null);
//     const [downloadData, setDownloadData] = useState(null);
//
//     return (
//       <div>
//         <nav className="nav">
//           <span className="logo">AKTE</span>
//           <span className="subtitle">Adaptive Knowledge Transformation Engine</span>
//         </nav>
//
//         <div className="progress">
//           {['Upload', 'Quiz', 'Level', 'Transform'].map((label, i) => (
//             <span key={label}
//               className={`step ${ ['upload','quiz','level','download'][i] === page ? 'active' : '' }`}>
//               {i + 1}. {label}
//             </span>
//           ))}
//         </div>
//
//         {page === 'upload'   && <Upload userId={USER_ID}
//                                   onDone={(fname, qs) => { setFilename(fname); setQuestions(qs); setPage('quiz'); }} />}
//         {page === 'quiz'     && <Quiz userId={USER_ID} filename={filename} questions={questions}
//                                   onDone={(r) => { setQuizResult(r); setPage('level'); }} />}
//         {page === 'level'    && <LevelResult result={quizResult} userId={USER_ID} filename={filename}
//                                   onTransform={(d) => { setDownloadData(d); setPage('download'); }} />}
//         {page === 'download' && <Download data={downloadData}
//                                   onReset={() => { setPage('upload'); setFilename(null); }} />}
//       </div>
//     );
//   }
// =============================================================================

import { useState } from 'react';
import Upload      from './components/Upload';
import Quiz        from './components/Quiz';
import LevelResult from './components/LevelResult';
import Download    from './components/Download';
import './App.css';

const USER_ID = 'user_' + Math.random().toString(36).slice(2, 10);

export default function App() {
  // TODO: implement this — full guide above
}
