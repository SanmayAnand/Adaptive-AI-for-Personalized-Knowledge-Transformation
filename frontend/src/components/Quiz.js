// =============================================================================
// src/components/Quiz.js
// Renders MCQ + self-assessment questions.
// Calls quiz_handler action='score' on submit.
// "I don't know" option counts as no answer (wrong) - pushes level down.
// =============================================================================
import { useState } from 'react';
import { scoreQuiz } from '../api';
import '../styles/quiz.css';

export default function Quiz({ userId, filename, docId, quizData, onScored }) {
  const { mcq_questions = [], self_questions = [], word_count = 0, extraction_note = 'ok' } = quizData || {};

  // answers: { "0": "A", "1": "B", ... } for MCQ
  // "IDK" is a special value meaning "I don't know" - treated as wrong on scoring
  const [mcqAnswers,  setMcqAnswers]  = useState({});
  const [selfAnswers, setSelfAnswers] = useState({});
  const [submitting,  setSubmitting]  = useState(false);
  const [error,       setError]       = useState('');

  const allMcqAnswered  = mcq_questions.every((_, i) => mcqAnswers[String(i)]);
  const allSelfAnswered = self_questions.every(q => selfAnswers[q.id]);
  const canSubmit       = allMcqAnswered && allSelfAnswered;

  async function handleSubmit() {
    if (!canSubmit) {
      setError('Please answer all questions before submitting.');
      return;
    }
    setSubmitting(true);
    setError('');

    // Replace "IDK" answers with a value that won't match any correct answer
    const cleanedMcqAnswers = {};
    Object.entries(mcqAnswers).forEach(([k, v]) => {
      cleanedMcqAnswers[k] = v === 'IDK' ? '__idk__' : v;
    });

    try {
      const result = await scoreQuiz(
        userId, docId, filename,
        mcq_questions, cleanedMcqAnswers, selfAnswers,
        word_count, extraction_note
      );
      onScored(result);
    } catch (err) {
      setError(err.message || 'Scoring failed. Please try again.');
      setSubmitting(false);
    }
  }

  return (
    <div className="page-container quiz-page">
      <div className="page-header">
        <div className="breadcrumb">
          <span className="crumb-doc">{filename}</span>
        </div>
        <h1 className="page-title">Knowledge check</h1>
        <p className="page-subtitle">
          These questions are about <strong>{filename}</strong>.
          Your answers help AKTE calibrate how much to explain vs. compress.
        </p>
        {word_count > 0 && (
          <span className="word-badge">{word_count.toLocaleString()} words extracted</span>
        )}
      </div>

      {/* Progress bar */}
      <div className="quiz-progress-bar-outer">
        <div className="quiz-progress-bar-fill" style={{ width: `${Math.round((Object.keys(mcqAnswers).length + Object.keys(selfAnswers).length) / (mcq_questions.length + self_questions.length) * 100)}%` }} />
      </div>

      {/* MCQ Questions */}
      <section className="quiz-section">
        <h2 className="section-label">Document questions</h2>
        {mcq_questions.map((q, i) => (
          <QuestionCard
            key={i}
            index={i}
            total={mcq_questions.length}
            question={q.question}
            options={q.options}
            selected={mcqAnswers[String(i)]}
            onSelect={key => setMcqAnswers(prev => ({ ...prev, [String(i)]: key }))}
          />
        ))}
      </section>

      {/* Self-assessment questions */}
      <section className="quiz-section">
        <h2 className="section-label">About you</h2>
        <p className="section-note">
          These don't affect your score - they help fine-tune the rewrite.
        </p>
        {self_questions.map(q => (
          <SelfQuestionCard
            key={q.id}
            question={q.question}
            options={q.options}
            selected={selfAnswers[q.id]}
            onSelect={val => setSelfAnswers(prev => ({ ...prev, [q.id]: val }))}
          />
        ))}
      </section>

      {error && <div className="quiz-error"><span>⚠</span> {error}</div>}

      <div className="quiz-footer">
        <div className="answered-count">
          {Object.keys(mcqAnswers).length} / {mcq_questions.length} answered
        </div>
        <button
          className="btn-primary btn-lg"
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
        >
          {submitting ? 'Scoring…' : 'Submit answers →'}
        </button>
      </div>
    </div>
  );
}

// ── MCQ card ──────────────────────────────────────────────────────────────────
function QuestionCard({ index, total, question, options, selected, onSelect }) {
  return (
    <div className={`q-card ${selected ? 'q-card--answered' : ''}`}>
      <div className="q-meta">
        <span className="q-num">Q{index + 1}</span>
        <span className="q-of">of {total}</span>
      </div>
      <p className="q-text">{question}</p>
      <div className="q-options">
        {Object.entries(options).map(([key, text]) => (
          <label
            key={key}
            className={`q-option ${selected === key ? 'q-option--selected' : ''}`}
          >
            <input
              type="radio"
              name={`mcq_${index}`}
              value={key}
              checked={selected === key}
              onChange={() => onSelect(key)}
            />
            <span className="q-option-key">{key}</span>
            <span className="q-option-text">{text}</span>
          </label>
        ))}

        {/* I don't know option */}
        <label
          className={`q-option q-option--idk ${selected === 'IDK' ? 'q-option--selected q-option--idk-selected' : ''}`}
        >
          <input
            type="radio"
            name={`mcq_${index}`}
            value="IDK"
            checked={selected === 'IDK'}
            onChange={() => onSelect('IDK')}
          />
          <span className="q-option-key">?</span>
          <span className="q-option-text">I don't know</span>
        </label>
      </div>
    </div>
  );
}

// ── Self-assessment card ──────────────────────────────────────────────────────
function SelfQuestionCard({ question, options, selected, onSelect }) {
  return (
    <div className={`q-card q-card--self ${selected ? 'q-card--answered' : ''}`}>
      <p className="q-text">{question}</p>
      <div className="q-options q-options--grid">
        {Object.entries(options).map(([key, text]) => (
          <label
            key={key}
            className={`q-option q-option--pill ${selected === key ? 'q-option--selected' : ''}`}
          >
            <input
              type="radio"
              name={`self_${question}`}
              value={key}
              checked={selected === key}
              onChange={() => onSelect(key)}
            />
            <span className="q-option-text">{text}</span>
          </label>
        ))}
      </div>
    </div>
  );
}