// src/components/Upload.js - Enhanced landing page with typewriter + manual hint nav
import { useState, useRef, useEffect, useCallback } from 'react';
import { getUploadUrl, uploadFileToS3, pollUntilReady, generateQuiz } from '../api';
import '../styles/upload.css';

const ACCEPTED = '.pdf,.docx';

const PHRASES = [
  'rewritten for you.',
  'adapted to your level.',
  'simplified to basics.',
  'condensed to essentials.',
  'your personal textbook.',
];

const FEATURE_HINTS = [
  { icon: '✍️', title: 'Highlight as you read',     body: 'Select any text in your document and highlight it in yellow, green, blue or pink - saved for your next session.' },
  { icon: '📝', title: 'Take inline notes',          body: 'Click any paragraph to attach a personal note right there in the text - with the quoted sentence for context.' },
  { icon: '🔀', title: 'Toggle original vs rewrite', body: 'Switch between the original document and your personalised version instantly - without losing your page position.' },
  { icon: '💡', title: 'Clickable key terms',        body: 'Underlined words in the text are annotated - click any one to get a two-sentence explanation in a popup.' },
  { icon: '🎮', title: 'Play to Learn',              body: 'When you\'re done reading, test yourself with a flashcard game built entirely from your document\'s content.' },
  { icon: '⬇️', title: 'Download your version',     body: 'Export your personalised document as a clean PDF - your highlights and notes are printed right inside it.' },
];

// Typewriter hook
function useTypewriter(phrases, speed = 60, pause = 1800) {
  const [displayed, setDisplayed] = useState('');
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [deleting, setDeleting]   = useState(false);
  const timeoutRef = useRef(null);

  useEffect(() => {
    const current = phrases[phraseIdx];
    function tick() {
      if (!deleting) {
        if (displayed.length < current.length) {
          setDisplayed(current.slice(0, displayed.length + 1));
          timeoutRef.current = setTimeout(tick, speed);
        } else {
          timeoutRef.current = setTimeout(() => setDeleting(true), pause);
        }
      } else {
        if (displayed.length > 0) {
          setDisplayed(current.slice(0, displayed.length - 1));
          timeoutRef.current = setTimeout(tick, speed / 2);
        } else {
          setDeleting(false);
          setPhraseIdx(i => (i + 1) % phrases.length);
        }
      }
    }
    timeoutRef.current = setTimeout(tick, speed);
    return () => clearTimeout(timeoutRef.current);
  }, [displayed, deleting, phraseIdx, phrases, speed, pause]);

  return displayed;
}

function FeatureHintCarousel({ active }) {
  const [idx, setIdx]   = useState(0);
  const [fade, setFade] = useState(true);
  const timerRef        = useRef(null);

  const goTo = useCallback((next) => {
    setFade(false);
    setTimeout(() => { setIdx(next); setFade(true); }, 320);
  }, []);

  useEffect(() => {
    if (!active) return;
    timerRef.current = setInterval(() => {
      goTo((idx + 1) % FEATURE_HINTS.length);
    }, 3800);
    return () => clearInterval(timerRef.current);
  }, [active, idx, goTo]);

  const handlePrev = () => {
    clearInterval(timerRef.current);
    goTo((idx - 1 + FEATURE_HINTS.length) % FEATURE_HINTS.length);
  };
  const handleNext = () => {
    clearInterval(timerRef.current);
    goTo((idx + 1) % FEATURE_HINTS.length);
  };

  if (!active) return null;
  const hint = FEATURE_HINTS[idx];

  return (
    <div className="hint-carousel">
      <div className={`hint-card ${fade ? 'hint-card--in' : 'hint-card--out'}`}>
        <span className="hint-icon">{hint.icon}</span>
        <div className="hint-body">
          <strong className="hint-title">{hint.title}</strong>
          <p className="hint-desc">{hint.body}</p>
        </div>
      </div>
      <div className="hint-nav">
        <button className="hint-prev" onClick={handlePrev}>‹</button>
        <div className="hint-dots">
          {FEATURE_HINTS.map((_, i) => (
            <span key={i} className={`hint-dot ${i === idx ? 'hint-dot--active' : ''}`}
              onClick={() => { clearInterval(timerRef.current); goTo(i); }}
              style={{ cursor: 'pointer' }}
            />
          ))}
        </div>
        <button className="hint-next" onClick={handleNext}>›</button>
      </div>
    </div>
  );
}

export default function Upload({ userId, onDone, onQuizLoaded }) {
  const [file, setFile]         = useState(null);
  const [status, setStatus]     = useState('idle');
  const [message, setMessage]   = useState('');
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const typewriterText = useTypewriter(PHRASES);
  const isLoading    = ['uploading', 'ocr', 'quiz'].includes(status);
  const isOcrOrQuiz  = status === 'ocr' || status === 'quiz';

  function handleDrop(e) {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  async function handleStart() {
    if (!file) return;
    try {
      setStatus('uploading');
      setMessage('Getting upload URL…');
      const uploadMeta = await getUploadUrl(userId, file.name);

      setMessage('Uploading your document…');
      await uploadFileToS3(uploadMeta.upload_url, file, uploadMeta.content_type);

      setStatus('ocr');
      setMessage('Extracting text from your document…');
      setProgress(0);
      const readyResult = await pollUntilReady(
        userId, uploadMeta.filename,
        (attempt, max) => setProgress(Math.round((attempt / max) * 60)),
      );

      setStatus('quiz');
      setMessage('Writing quiz questions about your document…');
      setProgress(70);
      const quizData = await generateQuiz(userId, uploadMeta.filename);
      setProgress(100);

      onQuizLoaded(quizData);
      onDone({ filename: uploadMeta.filename, docId: readyResult.doc_id });

    } catch (err) {
      setStatus('error');
      setMessage(err.message || 'Something went wrong. Please try again.');
    }
  }

  return (
    <div className="upload-page-shell">
      {/* ── Hero ── */}
      <div className="upload-hero">
        <div className="upload-hero-eyebrow fade-up">Adaptive Knowledge Engine</div>
        <h1 className="upload-hero-title fade-up-1">
          Your document,<br />
          <span className="upload-hero-line2">{typewriterText}</span>
        </h1>
        <p className="upload-hero-sub fade-up-2">
          Upload any PDF or Word doc. AKTE reads it, quizzes you on it,
          then rewrites it to exactly match your knowledge level -
          with clickable terms, highlights, notes, and a study game built in.
        </p>
      </div>

      {/* ── Upload + loading ── */}
      <div className="page-container upload-page">
        <div className="upload-area-wrapper">
          {!isLoading ? (
            <>
              <div
                className={`upload-dropzone ${file ? 'has-file' : ''} ${dragOver ? 'drag-active' : ''}`}
                onDrop={handleDrop}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => inputRef.current?.click()}
              >
                <input ref={inputRef} type="file" accept={ACCEPTED}
                  style={{ display: 'none' }} onChange={e => setFile(e.target.files[0])} />
                {!file && (
                  <div className="dropzone-empty">
                    <div className="drop-icon">📄</div>
                    <p className="drop-label">Drop a PDF or Word document here</p>
                    <p className="drop-sub">or click to browse · PDF & DOCX supported</p>
                  </div>
                )}
                {file && (
                  <div className="dropzone-file">
                    <div className="file-icon">{file.name.endsWith('.pdf') ? '📕' : '📘'}</div>
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">{(file.size / 1024).toFixed(0)} KB</span>
                    </div>
                    <button className="file-remove" onClick={e => { e.stopPropagation(); setFile(null); }}>×</button>
                  </div>
                )}
              </div>
              {status === 'error' && <div className="upload-error"><span>⚠</span> {message}</div>}
              {file && (
                <button className="btn-primary btn-lg upload-submit" onClick={handleStart}>
                  Upload &amp; Start Quiz →
                </button>
              )}
            </>
          ) : (
            <div className="upload-loading-shell">
              <div className="upload-loading-top">
                <div className="loading-spinner" />
                <p className="loading-label">{message}</p>
                {progress > 0 && (
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progress}%` }} />
                  </div>
                )}
                <p className="loading-sub">
                  {status === 'uploading' && 'Sending your file securely to AWS S3…'}
                  {status === 'ocr'       && 'Running OCR and text extraction on your document…'}
                  {status === 'quiz'      && 'AI is reading your document and composing questions…'}
                </p>
              </div>
              <div className="hint-section-label">While you wait - here's what you can do in AKTE</div>
              <FeatureHintCarousel active={isOcrOrQuiz} />
            </div>
          )}
        </div>

        {/* How it works */}
        {!isLoading && (
          <div className="upload-how">
            <div className="how-step">
              <span className="step-num">1</span>
              <div>
                <div className="how-step-text">Upload your document</div>
                <div className="how-step-sub">PDF or Word, any size</div>
              </div>
            </div>
            <div className="how-arrow">→</div>
            <div className="how-step">
              <span className="step-num">2</span>
              <div>
                <div className="how-step-text">Answer 5 questions about it</div>
                <div className="how-step-sub">Sets your knowledge level</div>
              </div>
            </div>
            <div className="how-arrow">→</div>
            <div className="how-step">
              <span className="step-num">3</span>
              <div>
                <div className="how-step-text">Get a version rewritten for you</div>
                <div className="how-step-sub">Expanded or condensed to your level</div>
              </div>
            </div>
            <div className="how-arrow">→</div>
            <div className="how-step">
              <span className="step-num">4</span>
              <div>
                <div className="how-step-text">Play to reinforce what you learned</div>
                <div className="how-step-sub">Flashcard game built from your doc</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Features grid */}
      {!isLoading && !file && (
        <div className="features-showcase">
          <div className="features-showcase-inner">
            <h2 className="features-showcase-title">Everything you need to actually learn</h2>
            <p className="features-showcase-sub">Not just a summary tool - a full reading environment built for deep understanding.</p>
            <div className="features-grid">
              {FEATURE_HINTS.map(h => (
                <div key={h.title} className="features-grid-item">
                  <div className="features-grid-icon">{h.icon}</div>
                  <div>
                    <div className="features-grid-name">{h.title}</div>
                    <div className="features-grid-desc">{h.body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}