// =============================================================================
// src/components/StudyView.js
// The main reading experience.
// - Notion-style clean page layout
// - Toggle between original and transformed document
// - Clickable/hoverable annotated terms with popup explanations
// - Download button
// =============================================================================
import { useState, useCallback, useRef, useEffect } from 'react';
import '../styles/study.css';

const LEVEL_META = {
  beginner:     { emoji: '🌱', label: 'Beginner',     color: '#2d6a4f' },
  intermediate: { emoji: '📖', label: 'Intermediate', color: '#1d3557' },
  expert:       { emoji: '⚡', label: 'Expert',       color: '#7b2d8b' },
};

const INTENT_META = {
  studying:   { icon: '🎯', label: 'Study Mode' },
  applying:   { icon: '🔧', label: 'Application Mode' },
  explaining: { icon: '💬', label: 'Explain Mode' },
  exploring:  { icon: '🔍', label: 'Explore Mode' },
};

const TYPE_COLORS = {
  concept:    '#2563eb',
  formula:    '#7c3aed',
  person:     '#b45309',
  definition: '#065f46',
};

export default function StudyView({ data, onNewDoc }) {
  const {
    downloadUrl,
    level,
    intent,
    annotations = [],
    transformedText,
    originalText,
    filename,
  } = data;

  const [view, setView]               = useState('transformed');   // 'transformed' | 'original'
  const [activeAnnotation, setActive] = useState(null);            // annotation object or null
  const [popupPos, setPopupPos]       = useState({ x: 0, y: 0 }); // popup anchor position
  const [showAnnotationPanel, setShowPanel] = useState(false);
  const contentRef = useRef(null);

  const levelMeta  = LEVEL_META[level]  || LEVEL_META.intermediate;
  const intentMeta = INTENT_META[intent] || INTENT_META.studying;

  const currentText = view === 'transformed' ? transformedText : (originalText || transformedText);

  // ── Annotation click handler ──────────────────────────────────────────────
  const handleAnnotationClick = useCallback((annotation, event) => {
    const rect = event.target.getBoundingClientRect();
    setActive(annotation);
    setPopupPos({ x: rect.left, y: rect.bottom + 8 });
  }, []);

  // Close popup on outside click
  useEffect(() => {
    function handleClick(e) {
      if (!e.target.closest('.annotation-popup') && !e.target.closest('.annotated-term')) {
        setActive(null);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // ── Render text with annotations ─────────────────────────────────────────
  // Finds annotation terms in the text and wraps them in clickable spans.
  function renderAnnotatedText(text) {
    if (!text) return null;
    if (!annotations.length) return <TextBlock text={text} />;

    // Build a sorted list of all annotation terms found in text
    const found = [];
    for (const ann of annotations) {
      const term = ann.term;
      const re   = new RegExp(`\\b${escapeRegex(term)}\\b`, 'gi');
      let match;
      while ((match = re.exec(text)) !== null) {
        found.push({ start: match.index, end: match.index + match[0].length, ann, matched: match[0] });
      }
    }

    if (!found.length) return <TextBlock text={text} />;

    // Sort by position, remove overlaps
    found.sort((a, b) => a.start - b.start);
    const deduped = [];
    let cursor = 0;
    for (const f of found) {
      if (f.start >= cursor) { deduped.push(f); cursor = f.end; }
    }

    // Build React nodes
    const nodes = [];
    let pos = 0;
    for (const f of deduped) {
      if (f.start > pos) {
        nodes.push(<TextBlock key={`t${pos}`} text={text.slice(pos, f.start)} />);
      }
      nodes.push(
        <AnnotatedTerm
          key={`a${f.start}`}
          ann={f.ann}
          matched={f.matched}
          onClick={handleAnnotationClick}
        />
      );
      pos = f.end;
    }
    if (pos < text.length) {
      nodes.push(<TextBlock key={`t${pos}`} text={text.slice(pos)} />);
    }
    return nodes;
  }

  return (
    <div className="study-shell">
      {/* ── Top bar ── */}
      <div className="study-topbar">
        <div className="study-topbar-left">
          <button className="topbar-back" onClick={onNewDoc}>← New document</button>
          <span className="topbar-filename">{filename}</span>
        </div>
        <div className="study-topbar-right">
          <div className="view-toggle">
            <button
              className={`toggle-btn ${view === 'transformed' ? 'active' : ''}`}
              onClick={() => setView('transformed')}
            >
              {levelMeta.emoji} Personalised
            </button>
            {originalText && (
              <button
                className={`toggle-btn ${view === 'original' ? 'active' : ''}`}
                onClick={() => setView('original')}
              >
                📄 Original
              </button>
            )}
          </div>
          <button
            className="topbar-annotations"
            onClick={() => setShowPanel(p => !p)}
            title="Key terms"
          >
            🔖 {annotations.length} terms
          </button>
          <a
            href={downloadUrl}
            download
            className="topbar-download"
          >
            ↓ Download
          </a>
        </div>
      </div>

      <div className="study-body">
        {/* ── Main content ── */}
        <article className="study-page" ref={contentRef}>
          {/* Document title block — Notion style */}
          <div className="study-doc-header">
            <div className="doc-level-badge" style={{ color: levelMeta.color }}>
              {levelMeta.emoji} {levelMeta.label} version
            </div>
            <h1 className="doc-title">{stripExtension(filename)}</h1>
            <div className="doc-meta-row">
              <span className="doc-meta-item">{intentMeta.icon} {intentMeta.label}</span>
              {view === 'original' && (
                <span className="doc-meta-item doc-meta-original">📄 Original document</span>
              )}
            </div>
          </div>

          {/* Notion-style callout when viewing original */}
          {view === 'original' && (
            <div className="callout callout--info">
              <span>📄</span>
              <span>
                This is the original extracted text.{' '}
                <button className="callout-link" onClick={() => setView('transformed')}>
                  Switch to your {levelMeta.label} version →
                </button>
              </span>
            </div>
          )}

          {/* The actual document text */}
          <div className="doc-content">
            {renderAnnotatedText(currentText)}
          </div>
        </article>

        {/* ── Annotation panel (sidebar) ── */}
        {showAnnotationPanel && annotations.length > 0 && (
          <aside className="annotation-panel">
            <div className="ann-panel-header">
              <h3>Key terms</h3>
              <button className="ann-panel-close" onClick={() => setShowPanel(false)}>×</button>
            </div>
            <div className="ann-panel-list">
              {annotations.map((ann, i) => (
                <div key={i} className="ann-panel-item">
                  <div className="ann-term-row">
                    <span
                      className="ann-term-text"
                      style={{ borderColor: TYPE_COLORS[ann.type] || '#999' }}
                    >
                      {ann.term}
                    </span>
                    <span className="ann-type-badge">{ann.type}</span>
                  </div>
                  <p className="ann-short">{ann.short}</p>
                  <p className="ann-detail">{ann.detail}</p>
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>

      {/* ── Annotation popup ── */}
      {activeAnnotation && (
        <AnnotationPopup
          ann={activeAnnotation}
          pos={popupPos}
          onClose={() => setActive(null)}
        />
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

// Renders a plain text block, converting newlines to paragraphs
function TextBlock({ text }) {
  const lines = text.split('\n');
  return (
    <>
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="text-spacer" />;
        // Markdown-style bold for **terms**
        const rendered = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Heading detection: lines starting with ## or all-caps short lines
        if (line.startsWith('## ') || line.startsWith('# ')) {
          const headingText = line.replace(/^#+ /, '');
          return <h2 key={i} className="doc-heading" dangerouslySetInnerHTML={{ __html: headingText }} />;
        }
        if (line.startsWith('Key takeaway:') || line.startsWith('Think of it like:') || line.startsWith('In practice:')) {
          return (
            <div key={i} className="callout callout--highlight">
              <span>💡</span>
              <span dangerouslySetInnerHTML={{ __html: rendered }} />
            </div>
          );
        }
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return <li key={i} className="doc-li" dangerouslySetInnerHTML={{ __html: rendered.slice(2) }} />;
        }
        return <p key={i} className="doc-para" dangerouslySetInnerHTML={{ __html: rendered }} />;
      })}
    </>
  );
}

// A single annotated term inline in the text
function AnnotatedTerm({ ann, matched, onClick }) {
  const color = TYPE_COLORS[ann.type] || '#2563eb';
  return (
    <span
      className="annotated-term"
      style={{
        borderBottomColor: color,
        '--ann-color': color,
      }}
      onClick={e => onClick(ann, e)}
      title={ann.short}
    >
      {matched}
    </span>
  );
}

// Floating popup when an annotation is clicked
function AnnotationPopup({ ann, pos, onClose }) {
  const color = TYPE_COLORS[ann.type] || '#2563eb';

  // Clamp to viewport
  const x = Math.min(pos.x, window.innerWidth - 340);
  const y = pos.y;

  return (
    <div
      className="annotation-popup"
      style={{ left: x, top: y }}
    >
      <div className="ann-popup-header" style={{ borderColor: color }}>
        <span className="ann-popup-term">{ann.term}</span>
        <span className="ann-popup-type" style={{ color }}>{ann.type}</span>
        <button className="ann-popup-close" onClick={onClose}>×</button>
      </div>
      <p className="ann-popup-short">{ann.short}</p>
      <p className="ann-popup-detail">{ann.detail}</p>
    </div>
  );
}

// =============================================================================
// Utils
// =============================================================================
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function stripExtension(filename) {
  return filename.replace(/\.[^.]+$/, '').replace(/_/g, ' ');
}