// =============================================================================
// src/components/LevelResult.js
// Shows detected level, score breakdown, intent.
// Triggers transform → hands off to StudyView.
// =============================================================================
import { useState } from 'react';
import { transformDocument, fetchDocumentText } from '../api';
import '../styles/level.css';

const LEVEL_META = {
  beginner: {
    emoji: '🌱',
    label: 'Beginner',
    color: '#2d6a4f',
    bg: '#d8f3dc',
    desc: 'Inline explanations and analogies will be added throughout the document.',
  },
  intermediate: {
    emoji: '📖',
    label: 'Intermediate',
    color: '#1d3557',
    bg: '#e0f0ff',
    desc: 'Complex terms will be clarified. Core content stays intact.',
  },
  expert: {
    emoji: '⚡',
    label: 'Expert',
    color: '#7b2d8b',
    bg: '#f3e8ff',
    desc: 'Document condensed. All obvious content removed. Just the essentials.',
  },
};

const INTENT_LABELS = {
  studying:   { icon: '🎯', label: 'Study Mode' },
  applying:   { icon: '🔧', label: 'Application Mode' },
  explaining: { icon: '💬', label: 'Explain-to-Others Mode' },
  exploring:  { icon: '🔍', label: 'Exploration Mode' },
};

export default function LevelResult({ userId, filename, docId, scoreData, onTransformDone }) {
  const { score, level, intent } = scoreData;
  const meta = LEVEL_META[level] || LEVEL_META.intermediate;
  const intentMeta = INTENT_LABELS[intent] || INTENT_LABELS.studying;

  const [loading,  setLoading]  = useState(false);
  const [status,   setStatus]   = useState('');
  const [error,    setError]    = useState('');

  async function handleTransform() {
    setLoading(true);
    setError('');
    try {
      setStatus('Rewriting your document with AI… (this takes 30–90 seconds)');
      const result = await transformDocument(userId, filename, docId);
      // result = { download_url, level, intent, annotations, s3_key }

      // Fetch the actual text content for inline reading view
      setStatus('Loading your personalised document…');
      const transformedText = await fetchDocumentText(result.download_url);

      onTransformDone({
        downloadUrl:     result.download_url,
        level:           result.level,
        intent:          result.intent,
        annotations:     result.annotations || [],
        transformedText: transformedText,
        originalText:    null,   // optional: could load original extracted text too
        filename:        filename,
        docId:           docId,
      });
    } catch (err) {
      setError(err.message || 'Transform failed. Please try again.');
      setLoading(false);
      setStatus('');
    }
  }

  return (
    <div className="page-container level-page">
      <div className="page-header">
        <div className="breadcrumb">
          <span className="crumb-doc">{filename}</span>
        </div>
        <h1 className="page-title">Your knowledge level</h1>
      </div>

      <div className="level-card" style={{ borderColor: meta.color, background: meta.bg }}>
        <div className="level-badge-row">
          <span className="level-emoji">{meta.emoji}</span>
          <span className="level-name" style={{ color: meta.color }}>{meta.label}</span>
        </div>
        <p className="level-desc">{meta.desc}</p>
        <div className="level-score">
          Score: <strong>{score} / {scoreData.total || 5}</strong>
        </div>
      </div>

      <div className="intent-row">
        <span className="intent-icon">{intentMeta.icon}</span>
        <div>
          <div className="intent-label">{intentMeta.label}</div>
          <div className="intent-sub">Your reading intent shapes how the content is framed.</div>
        </div>
      </div>

      <div className="what-happens">
        <h3 className="what-title">What happens next</h3>
        <ul className="what-list">
          <li>The full document is rewritten for the <strong>{meta.label}</strong> level</li>
          <li>Key terms become clickable — hover for instant explanations</li>
          <li>You can toggle between the original and personalised version</li>
          <li>Download the personalised version anytime</li>
        </ul>
      </div>

      {error && <div className="level-error"><span>⚠</span> {error}</div>}

      {loading ? (
        <div className="transform-loading">
          <div className="loading-spinner" />
          <p>{status}</p>
          <p className="transform-note">
            Larger documents take longer. Don't close this tab.
          </p>
        </div>
      ) : (
        <button className="btn-primary btn-lg" onClick={handleTransform}>
          {meta.emoji} Generate my {meta.label} version →
        </button>
      )}
    </div>
  );
}