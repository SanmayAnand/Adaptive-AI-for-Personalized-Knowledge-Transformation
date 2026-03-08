// src/components/LevelResult.js
import { useState } from 'react';
import { transformDocument, fetchDocumentText } from '../api';
import '../styles/level.css';

const LEVEL_META = {
  beginner: {
    emoji: '🌱', label: 'Beginner', color: '#16a34a', bg: '#dcfce7',
    desc: 'Inline explanations and analogies will be added throughout the document.',
  },
  intermediate: {
    emoji: '📖', label: 'Intermediate', color: '#1d4ed8', bg: '#dbeafe',
    desc: 'Complex terms will be clarified. Core content stays intact.',
  },
  expert: {
    emoji: '⚡', label: 'Expert', color: '#7c3aed', bg: '#f3e8ff',
    desc: 'Document condensed. All obvious content removed. Just the essentials.',
  },
};

const INTENT_LABELS = {
  studying:   { icon: '🎯', label: 'Study Mode',            sub: 'Structured for retention and recall.' },
  applying:   { icon: '🔧', label: 'Application Mode',      sub: 'Focused on practical takeaways.' },
  explaining: { icon: '💬', label: 'Explain-to-Others Mode',sub: 'Framed for teaching and sharing.' },
  exploring:  { icon: '🔍', label: 'Exploration Mode',      sub: 'Contextualised for breadth and curiosity.' },
};

const STUDY_TIPS = [
  { icon: '✍️', text: <><strong>Highlight</strong> key ideas - select any text and pick a colour from the popup toolbar.</> },
  { icon: '📝', text: <><strong>Take notes</strong> inline - click any paragraph to attach a note right there in the text.</> },
  { icon: '🔀', text: <><strong>Toggle views</strong> - switch between the original and your personalised version at any time.</> },
  { icon: '💡', text: <><strong>Click underlined terms</strong> - every annotated word shows a definition popup when clicked.</> },
  { icon: '🎮', text: <><strong>Play to learn</strong> - a flashcard game built from your document is waiting at the bottom of the page.</> },
];

export default function LevelResult({ userId, filename, docId, scoreData, onTransformDone }) {
  const { score, level, intent } = scoreData;
  const meta       = LEVEL_META[level]  || LEVEL_META.intermediate;
  const intentMeta = INTENT_LABELS[intent] || INTENT_LABELS.studying;

  const [loading, setLoading] = useState(false);
  const [status,  setStatus]  = useState('');
  const [error,   setError]   = useState('');

  async function handleTransform() {
    setLoading(true); setError('');
    try {
      setStatus('Rewriting your document with AI… (30–90 seconds)');
      const result = await transformDocument(userId, filename, docId);

      let transformedText = result.transformed_text || null;
      if (!transformedText && result.download_url) {
        try {
          setStatus('Loading your personalised document…');
          transformedText = await fetchDocumentText(result.download_url);
        } catch(e) { console.warn('Fallback fetch failed:', e); }
      }
      if (!transformedText) throw new Error('No transformed text received from server.');

      onTransformDone({
        downloadUrl:     result.download_url,
        level:           result.level,
        intent:          result.intent,
        annotations:     result.annotations || [],
        transformedText,
        originalText:    result.original_text || null,
        filename,
        docId,
      });
    } catch(err) {
      setError(err.message || 'Transform failed. Please try again.');
      setLoading(false); setStatus('');
    }
  }

  return (
    <div className="page-container level-page">
      <div className="page-header fade-up">
        <div className="breadcrumb"><span className="crumb-doc">{filename}</span></div>
        <h1 className="page-title">Your knowledge level</h1>
        <p className="page-subtitle">We'll rewrite the document to fit exactly where you are.</p>
      </div>

      <div className="level-card fade-up-1" style={{ borderColor: meta.color, background: meta.bg }}>
        <div className="level-badge-row">
          <span className="level-emoji">{meta.emoji}</span>
          <span className="level-name" style={{ color: meta.color }}>{meta.label}</span>
        </div>
        <p className="level-desc">{meta.desc}</p>
        <div className="level-score">Score: <strong>{score} / {scoreData.total || 5}</strong></div>
      </div>

      <div className="intent-row fade-up-2">
        <span className="intent-icon">{intentMeta.icon}</span>
        <div>
          <div className="intent-label">{intentMeta.label}</div>
          <div className="intent-sub">{intentMeta.sub}</div>
        </div>
      </div>

      <div className="what-happens fade-up-3">
        <h3 className="what-title">What happens when you click generate</h3>
        <ul className="what-list">
          <li>The full document is rewritten for the <strong>{meta.label}</strong> level</li>
          <li>Key terms become <strong>clickable</strong> - hover for instant explanations</li>
          <li>You can toggle between the original and your personalised version</li>
          <li>Highlights, notes, and a study game are all built in</li>
        </ul>
      </div>

      {error && <div className="level-error"><span>⚠</span> {error}</div>}

      {loading ? (
        <div className="transform-loading">
          <div className="loading-spinner" />
          <p>{status}</p>
          <p className="transform-note">Larger documents take longer. Don't close this tab.</p>

          {/* Study tips while loading */}
          <div className="level-loading-tips">
            <div className="level-tips-label">While you wait - you'll be able to…</div>
            <div className="level-tips-list">
              {STUDY_TIPS.map((tip, i) => (
                <div key={i} className="level-tip-item">
                  <span className="level-tip-icon">{tip.icon}</span>
                  <span className="level-tip-text">{tip.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <button className="btn-primary btn-lg" onClick={handleTransform}>
          {meta.emoji} Generate my {meta.label} version →
        </button>
      )}
    </div>
  );
}