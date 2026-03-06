// =============================================================================
// src/components/Upload.js
// Handles: file select → getUploadUrl → PUT to S3 → poll check_ready → generate quiz
// =============================================================================
import { useState, useRef } from 'react';
import { getUploadUrl, uploadFileToS3, pollUntilReady, generateQuiz } from '../api';
import '../styles/upload.css';

const ACCEPTED = '.pdf,.docx';

export default function Upload({ userId, onDone, onQuizLoaded }) {
  const [file, setFile]         = useState(null);
  const [status, setStatus]     = useState('idle'); // idle | uploading | ocr | quiz | error
  const [message, setMessage]   = useState('');
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  async function handleStart() {
    if (!file) return;

    try {
      // ── Step 1: Get pre-signed URL ─────────────────────────────────────────
      setStatus('uploading');
      setMessage('Getting upload URL...');
      const uploadMeta = await getUploadUrl(userId, file.name);
      // uploadMeta = { upload_url, filename (sanitised), s3_key, content_type }

      // ── Step 2: PUT file directly to S3 ──────────────────────────────────
      setMessage('Uploading to S3...');
      await uploadFileToS3(uploadMeta.upload_url, file, uploadMeta.content_type);

      // ── Step 3: Poll until Person B's OCR is done ────────────────────────
      setStatus('ocr');
      setMessage('Extracting text from document...');
      setProgress(0);
      const readyResult = await pollUntilReady(
        userId,
        uploadMeta.filename,
        (attempt, max) => setProgress(Math.round((attempt / max) * 60)),
      );
      // readyResult = { ready: true, doc_id: "..." }

      // ── Step 4: Generate quiz questions ──────────────────────────────────
      setStatus('quiz');
      setMessage('Generating quiz questions about your document...');
      setProgress(70);
      const quizData = await generateQuiz(userId, uploadMeta.filename);
      setProgress(100);

      // Pass quiz data up — App.js will show the Quiz screen
      onQuizLoaded(quizData);
      onDone({ filename: uploadMeta.filename, docId: readyResult.doc_id });

    } catch (err) {
      setStatus('error');
      setMessage(err.message || 'Something went wrong. Please try again.');
    }
  }

  const isLoading = ['uploading', 'ocr', 'quiz'].includes(status);

  return (
    <div className="page-container upload-page">
      <div className="page-header">
        <h1 className="page-title">New document</h1>
        <p className="page-subtitle">
          Upload a PDF or Word document. AKTE will read it, quiz you on it,
          then rewrite it to match your knowledge level.
        </p>
      </div>

      <div className="upload-area-wrapper">
        <div
          className={`upload-dropzone ${file ? 'has-file' : ''} ${isLoading ? 'loading' : ''}`}
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => !isLoading && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            style={{ display: 'none' }}
            onChange={e => setFile(e.target.files[0])}
          />

          {!file && !isLoading && (
            <div className="dropzone-empty">
              <div className="drop-icon">📄</div>
              <p className="drop-label">Drop a PDF or Word document here</p>
              <p className="drop-sub">or click to browse</p>
            </div>
          )}

          {file && !isLoading && (
            <div className="dropzone-file">
              <div className="file-icon">{file.name.endsWith('.pdf') ? '📕' : '📘'}</div>
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{(file.size / 1024).toFixed(0)} KB</span>
              </div>
              <button
                className="file-remove"
                onClick={e => { e.stopPropagation(); setFile(null); }}
              >×</button>
            </div>
          )}

          {isLoading && (
            <div className="dropzone-loading">
              <div className="loading-spinner" />
              <p className="loading-label">{message}</p>
              {progress > 0 && (
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
              )}
            </div>
          )}
        </div>

        {status === 'error' && (
          <div className="upload-error">
            <span className="error-icon">⚠</span> {message}
          </div>
        )}

        {file && !isLoading && (
          <button className="btn-primary btn-lg" onClick={handleStart}>
            Upload &amp; Start Quiz →
          </button>
        )}
      </div>

      <div className="upload-how">
        <div className="how-step">
          <span className="step-num">1</span>
          <span>Upload your document</span>
        </div>
        <div className="how-arrow">→</div>
        <div className="how-step">
          <span className="step-num">2</span>
          <span>Answer 5 questions about it</span>
        </div>
        <div className="how-arrow">→</div>
        <div className="how-step">
          <span className="step-num">3</span>
          <span>Get a version rewritten for your level</span>
        </div>
      </div>
    </div>
  );
}