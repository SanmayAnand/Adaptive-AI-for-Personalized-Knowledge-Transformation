// =============================================================================
// src/components/StudyView.js
// Features:
//   • Real inline text highlighting (Yellow / Green / Blue / Pink)
//   • Multiple notes per paragraph
//   • Notes capture a text quote when selected
//   • Floating toolbar appears on any text selection
//   • Notes panel sidebar shows all notes with their quotes
// =============================================================================
import React, { useState, useCallback, useEffect, useRef } from 'react';
import '../styles/study.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
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
  concept: '#2563eb', formula: '#7c3aed', person: '#b45309', definition: '#065f46',
};
const HL_COLORS = [
  { name: 'Yellow', value: '#fde68a' },
  { name: 'Green',  value: '#bbf7d0' },
  { name: 'Blue',   value: '#bfdbfe' },
  { name: 'Pink',   value: '#fbcfe8' },
];
const CALLOUT_MAP = {
  'Think of it like:':       '💡',
  'Key takeaway:':            '🔑',
  'Why this matters:':        '⭐',
  'In practice:':             '🔧',
  'One way to explain this:': '💬',
  'Interestingly,':           '✨',
  'What to explore next:':    '🗺️',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function stripAkteHeader(text) {
  if (!text) return '';
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length && !lines[i].startsWith('===')) i++;
  while (i < lines.length && (lines[i].startsWith('===') || lines[i].trim() === '')) i++;
  return lines.slice(i).join('\n').trim();
}

function uid() { return Math.random().toString(36).slice(2, 9); }

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function StudyView({ data, onNewDoc, onBackToDoc, docHistory }) {
  const { level, intent, annotations = [], transformedText, originalText, filename } = data;

  const levelMeta  = LEVEL_META[level]   || LEVEL_META.intermediate;
  const intentMeta = INTENT_META[intent] || INTENT_META.studying;

  const cleanTransformed = stripAkteHeader(transformedText || '');
  const cleanOriginal    = originalText ? stripAkteHeader(originalText) : null;
  const hasOriginal      = !!cleanOriginal;

  const [view,            setView]            = useState('transformed');
  const [showAnnotations, setShowAnnotations] = useState(false);
  const [showNotes,       setShowNotes]       = useState(false);
  const [activeAnn,       setActiveAnn]       = useState(null);
  const [annPos,          setAnnPos]          = useState({ x: 0, y: 0 });

  // highlights: [{ id, text, color }]
  const [highlights, setHighlights] = useState([]);

  // notes: { [paraIdx]: [{ id, quote, text }] }
  const [notes, setNotes] = useState({});

  // Floating selection toolbar: { x, y, selectedText } | null
  const [toolbar, setToolbar] = useState(null);

  // Inline note editor popup: { x, y, quote, paraIdx, editId, draft } | null
  const [notePopup, setNotePopup] = useState(null);

  // (game opens in same tab via handleLaunchGame - no iframe state needed)


  const isSplit    = view === 'split' && hasOriginal;
  const totalNotes = Object.values(notes).reduce((s, arr) => s + arr.length, 0);

  // Ref holds the last valid selection so toolbar actions can read it
  // even after React re-renders clear the toolbar state.
  const pendingSelection = useRef(null);

  // ── Selection detection ────────────────────────────────────────────────
  useEffect(() => {
    function onMouseUp(e) {
      if (e.target.closest('.sel-toolbar') || e.target.closest('.note-popup-editor')) return;

      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.toString().trim().length < 2) {
        setToolbar(null);
        pendingSelection.current = null;
        return;
      }

      const range = sel.getRangeAt(0);
      const selectedText = sel.toString().trim();
      if (!selectedText) { setToolbar(null); return; }

      // Find which para-block the selection starts in.
      // We walk up from the startContainer to find [data-para-idx].
      const startNode = range.startContainer.nodeType === 3
        ? range.startContainer.parentElement
        : range.startContainer;
      const paraBlock = startNode?.closest('[data-para-idx]');
      const paraIdx   = paraBlock ? parseInt(paraBlock.getAttribute('data-para-idx'), 10) : -1;

      // Compute character offset of the selection start within the para's
      // plain text (textContent). This is reliable and does NOT need regex later.
      let startOffset = -1, endOffset = -1;
      if (paraBlock && paraIdx >= 0) {
        // Get the textContent of just the .para-content div (excludes notes)
        const paraContent = paraBlock.querySelector('.para-content');
        if (paraContent) {
          // Walk all text nodes in paraContent to find absolute character offset
          const walker = document.createTreeWalker(paraContent, NodeFilter.SHOW_TEXT);
          let charCount = 0;
          let node;
          let foundStart = false, foundEnd = false;
          while ((node = walker.nextNode())) {
            const len = node.textContent.length;
            if (!foundStart && node === range.startContainer) {
              startOffset = charCount + range.startOffset;
              foundStart = true;
            }
            if (!foundEnd && node === range.endContainer) {
              endOffset = charCount + range.endOffset;
              foundEnd = true;
            }
            if (foundStart && foundEnd) break;
            charCount += len;
          }
        }
      }

      // Save everything to the ref - survives React re-renders.
      pendingSelection.current = { selectedText, paraIdx, startOffset, endOffset };

      const rect = range.getBoundingClientRect();
      setToolbar({
        x: rect.left + rect.width / 2,
        y: rect.top,   // viewport-relative, matches position:fixed
        selectedText,
        paraIdx,
        startOffset,
        endOffset,
      });
    }
    document.addEventListener('mouseup', onMouseUp);
    return () => document.removeEventListener('mouseup', onMouseUp);
  }, []);

  // Close toolbar / popup on outside click
  useEffect(() => {
    function onDown(e) {
      const inToolbar   = !!e.target.closest('.sel-toolbar');
      const inNotePopup = !!e.target.closest('.note-popup-editor');
      if (!inToolbar && !inNotePopup) {
        setToolbar(null);
        setNotePopup(null);
        pendingSelection.current = null;   // clear only when clicking outside
      }
      // pendingSelection.current is intentionally kept alive when clicking
      // inside the toolbar so swatch handlers can read it.
      if (!e.target.closest('.annotation-popup') && !e.target.closest('.annotated-term')) {
        setActiveAnn(null);
      }
    }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  // ── Highlight ────────────────────────────────────────────────────────────
  function applyHighlight(colorVal) {
    const sel = pendingSelection.current || (toolbar ? {
      selectedText: toolbar.selectedText,
      paraIdx: toolbar.paraIdx ?? -1,
      startOffset: toolbar.startOffset ?? -1,
      endOffset: toolbar.endOffset ?? -1,
    } : null);
    if (!sel?.selectedText) return;

    setHighlights(hs => [...hs, {
      id:          uid(),
      text:        sel.selectedText,   // kept for display in notes panel
      color:       colorVal,
      paraIdx:     sel.paraIdx,
      startOffset: sel.startOffset,
      endOffset:   sel.endOffset,
    }]);
    pendingSelection.current = null;
    window.getSelection()?.removeAllRanges();
    setToolbar(null);
  }

  function removeHighlight(id) {
    setHighlights(hs => hs.filter(h => h.id !== id));
  }

  // ── Notes ────────────────────────────────────────────────────────────────
  function openNoteEditor(quote, paraIdx, anchorX, anchorY) {
    // Use pendingSelection ref as fallback so the quote is never empty
    const safeQuote = quote || pendingSelection.current || '';
    setNotePopup({ quote: safeQuote, paraIdx, x: anchorX, y: anchorY, editId: null, draft: '' });
    pendingSelection.current = null;
    setToolbar(null);
    window.getSelection()?.removeAllRanges();
  }

  function saveNote(paraIdx, quote, text, editId) {
    if (!text.trim()) return;
    setNotes(n => {
      const arr = n[paraIdx] ? [...n[paraIdx]] : [];
      if (editId) {
        return { ...n, [paraIdx]: arr.map(x => x.id === editId ? { ...x, text, quote } : x) };
      }
      return { ...n, [paraIdx]: [...arr, { id: uid(), quote, text }] };
    });
    setNotePopup(null);
    setShowNotes(true);
  }

  function deleteNote(paraIdx, noteId) {
    setNotes(n => {
      const arr = (n[paraIdx] || []).filter(x => x.id !== noteId);
      if (!arr.length) { const copy = { ...n }; delete copy[paraIdx]; return copy; }
      return { ...n, [paraIdx]: arr };
    });
  }

  function editNote(paraIdx, note) {
    setNotePopup({
      quote:  note.quote,
      paraIdx,
      x: window.innerWidth / 2 - 170,
      y: 160,
      editId: note.id,
      draft:  note.text,
    });
  }

  // ── Annotation ──────────────────────────────────────────────────────────
  const handleAnnClick = useCallback((ann, e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setActiveAnn(ann);
    // r.bottom is viewport-relative; add scrollY because popup is position:absolute
    setAnnPos({
      x: Math.min(r.left + window.scrollX, window.innerWidth  - 340),
      y: r.bottom + window.scrollY + 8,
    });
  }, []);

  // ── Launch game ──────────────────────────────────────────────────────────
  // Opens the game in a new tab. The document text is stored in sessionStorage
  // so the game page can read it directly - no iframe, no CORS issues.
  function handleLaunchGame() {
    const cfg = {
      transformedText: cleanTransformed,
      filename:        filename || 'Document',
      level:           level   || 'intermediate',
      intent:          intent  || 'studying',
      annotations:     annotations || [],
    };
    // Store game config for the game page
    try {
      sessionStorage.setItem('AKTE_GAME_CONFIG', JSON.stringify(cfg));
    } catch(e) {
      console.warn('sessionStorage write failed, game will use demo mode', e);
    }
    // Save full study state so App.js can restore it when user comes back
    try {
      sessionStorage.setItem('AKTE_STUDY_RESTORE', JSON.stringify({
        studyData: data,
        docHistory: docHistory || [data],
      }));
    } catch(e) {}
    // Open game in same tab
    window.location.href = '/playing.html';
  }

  // ── PDF download ─────────────────────────────────────────────────────────
  function handleDownload() {
    const text  = view === 'original' && cleanOriginal ? cleanOriginal : cleanTransformed;
    const title = filename.replace(/\.[^.]+$/, '').replace(/_/g, ' ');
    const win   = window.open('', '_blank');
    win.document.write(`<!DOCTYPE html><html><head>
      <meta charset="utf-8"><title>${title}</title>
      <style>
        @page{margin:2cm}
        body{font-family:Georgia,serif;font-size:12pt;line-height:1.85;color:#111;max-width:680px;margin:0 auto}
        h1{font-size:22pt;font-family:Arial,sans-serif;margin-bottom:4px}
        h2{font-size:14pt;font-family:Arial,sans-serif;margin-top:2em;margin-bottom:.4em}
        .meta{color:#555;font-size:10pt;padding-bottom:16px;border-bottom:1px solid #ddd;margin-bottom:32px}
        p{margin-bottom:1.1em;text-align:justify}
        .callout{background:#fffbeb;border-left:3px solid #f59e0b;padding:8px 14px;margin:1em 0;font-size:11pt}
        .note-block{background:#eff6ff;border-left:3px solid #3b82f6;padding:8px 14px;margin:.4em 0 1em;font-size:11pt}
        .note-quote{font-style:italic;color:#555;margin-bottom:4px;font-size:10.5pt}
        mark{border-radius:2px;padding:0 1px}
      </style></head><body>
      <h1>${title}</h1>
      <div class="meta">${levelMeta.emoji} ${levelMeta.label} &nbsp;·&nbsp; ${intentMeta.icon} ${intentMeta.label}</div>
      ${buildPrintHtml(text, notes, highlights)}
    </body></html>`);
    win.document.close();
    setTimeout(() => { win.print(); win.close(); }, 400);
  }

  // ── Render text ───────────────────────────────────────────────────────────
  function renderText(text) {
    if (!text) return null;
    return text.split(/\n\s*\n/).filter(p => p.trim()).map((para, idx) => (
      <ParagraphBlock
        key={idx}
        paraIdx={idx}
        text={para.trim()}
        annotations={annotations}
        highlights={highlights}
        notes={notes[idx] || []}
        onAnnClick={handleAnnClick}
        onEditNote={(note) => editNote(idx, note)}
        onDeleteNote={(noteId) => deleteNote(idx, noteId)}
      />
    ));
  }

  return (
    <div className="study-shell">

      {/* ── Top bar ── */}
      <div className="study-topbar">
        <div className="study-topbar-left">
          <button className="topbar-back" onClick={onNewDoc}>← New doc</button>
          <span className="topbar-filename">{filename}</span>
        </div>
        <div className="study-topbar-right">
          <div className="view-toggle">
            <button className={`toggle-btn ${view === 'transformed' ? 'active' : ''}`}
              onClick={() => setView('transformed')}>{levelMeta.emoji} Personalised</button>
            {hasOriginal && <>
              <button className={`toggle-btn ${view === 'original' ? 'active' : ''}`}
                onClick={() => setView('original')}>📄 Original</button>
              <button className={`toggle-btn ${view === 'split' ? 'active' : ''}`}
                onClick={() => setView('split')}>⬜⬜ Side by side</button>
            </>}
          </div>

          <button
            className={`topbar-tool ${showNotes ? 'topbar-tool--active' : ''}`}
            onClick={() => setShowNotes(s => !s)}
          >
            📝 Notes{totalNotes > 0 ? ` (${totalNotes})` : ''}
          </button>

          {annotations.length > 0 && (
            <button
              className={`topbar-tool ${showAnnotations ? 'topbar-tool--active' : ''}`}
              onClick={() => setShowAnnotations(s => !s)}
            >
              🔖 {annotations.length} terms
            </button>
          )}

          <button className="topbar-download" onClick={handleDownload}>↓ Download PDF</button>
        </div>
      </div>

      {/* ── Floating selection toolbar ── */}
      {toolbar && (
        <div
          className="sel-toolbar"
          style={{
            position: 'fixed',
            left: Math.min(Math.max(toolbar.x - 140, 8), window.innerWidth - 300),
            top:  Math.max(toolbar.y - 54, 8),
            zIndex: 400,
          }}
        >
          <span className="sel-toolbar-label">Highlight:</span>
          {HL_COLORS.map(c => (
            <button
              key={c.value}
              className="sel-hl-swatch"
              style={{ background: c.value }}
              title={c.name}
              onMouseDown={e => { e.preventDefault(); applyHighlight(c.value); }}
            />
          ))}
          <div className="sel-toolbar-divider" />
          <button
            className="sel-note-btn"
            onMouseDown={e => {
              e.preventDefault();
              const r = e.currentTarget.getBoundingClientRect();
              openNoteEditor(toolbar.selectedText, -1, r.left, r.bottom + 10);
            }}
          >
            💬 Add note
          </button>
        </div>
      )}

      {/* ── Floating note editor ── */}
      {notePopup && (
        <NoteEditor
          popup={notePopup}
          onSave={(text) => saveNote(notePopup.paraIdx, notePopup.quote, text, notePopup.editId)}
          onCancel={() => setNotePopup(null)}
          onChange={(draft) => setNotePopup(p => ({ ...p, draft }))}
        />
      )}

      {/* ── Body ── */}
      <div className={`study-body ${isSplit ? 'study-body--split' : ''}`}>
        {isSplit ? (
          <>
            <article className="study-page study-page--split">
              <div className="split-panel-label">📄 Original extracted text</div>
              <div className="doc-content">{renderText(cleanOriginal)}</div>
            </article>
            <div className="split-divider" />
            <article className="study-page study-page--split">
              <div className="split-panel-label" style={{ color: levelMeta.color }}>
                {levelMeta.emoji} {levelMeta.label} version
              </div>
              <div className="doc-content">{renderText(cleanTransformed)}</div>
            </article>
          </>
        ) : (
          <article className="study-page">
            <div className="study-doc-header">
              <div className="doc-level-badge" style={{ color: levelMeta.color }}>
                {levelMeta.emoji} {levelMeta.label} version
              </div>
              <h1 className="doc-title">{filename.replace(/\.[^.]+$/, '').replace(/_/g, ' ')}</h1>
              <div className="doc-meta-row">
                <span className="doc-meta-item">{intentMeta.icon} {intentMeta.label}</span>
                {view === 'original' && (
                  <span className="doc-meta-item">
                    📄 Original &nbsp;
                    <button className="callout-link" onClick={() => setView('transformed')}>
                      → Switch to personalised
                    </button>
                  </span>
                )}
              </div>
            </div>
            <div className="doc-content">
              {renderText(view === 'original' ? (cleanOriginal || cleanTransformed) : cleanTransformed)}
            </div>
          </article>
        )}

        {/* ── Notes panel ── */}
        {showNotes && (
          <aside className="notes-panel">
            <div className="panel-header">
              <h3>📝 My Notes</h3>
              <button className="panel-close" onClick={() => setShowNotes(false)}>×</button>
            </div>

            {totalNotes === 0 && highlights.length === 0 ? (
              <p className="panel-empty">
                Select any text, then choose a highlight colour or click <strong>💬 Add note</strong>.
              </p>
            ) : (
              <>
                {totalNotes > 0 && (
                  <div className="notes-list">
                    {Object.entries(notes).flatMap(([paraIdx, arr]) =>
                      arr.map(note => (
                        <div key={note.id} className="note-entry">
                          {note.quote && (
                            <blockquote className="note-entry-quote">"{note.quote}"</blockquote>
                          )}
                          <p className="note-entry-text">{note.text}</p>
                          <div className="note-entry-actions">
                            <button onClick={() => editNote(Number(paraIdx), note)}>Edit</button>
                            <button onClick={() => deleteNote(Number(paraIdx), note.id)}>Delete</button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {highlights.length > 0 && (
                  <>
                    <div className="panel-section-header">🖊 Highlights</div>
                    <div className="highlights-list">
                      {highlights.map(h => (
                        <div key={h.id} className="highlight-entry" style={{ borderLeftColor: h.color, background: h.color + '55' }}>
                          <span className="highlight-entry-text">
                            "{h.text.slice(0, 70)}{h.text.length > 70 ? '…' : ''}"
                          </span>
                          <button className="highlight-entry-delete" onClick={() => removeHighlight(h.id)}>×</button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </aside>
        )}

        {/* ── Annotation panel ── */}
        {showAnnotations && annotations.length > 0 && (
          <aside className="annotation-panel">
            <div className="ann-panel-header">
              <h3>Key terms</h3>
              <button className="ann-panel-close" onClick={() => setShowAnnotations(false)}>×</button>
            </div>
            <div className="ann-panel-list">
              {annotations.map((ann, i) => (
                <div key={i} className="ann-panel-item">
                  <div className="ann-term-row">
                    <span className="ann-term-text" style={{ borderColor: TYPE_COLORS[ann.type] || '#999' }}>
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

      {/* ── Game launch - fixed bottom-right button ── */}
      <button className="game-fab" onClick={handleLaunchGame} title="Play to Learn">
        🎮
        <span className="game-fab-label">Play to Learn</span>
      </button>

      {/* ── Annotation popup ── */}
      {activeAnn && (
        <AnnotationPopup ann={activeAnn} pos={annPos} onClose={() => setActiveAnn(null)} />
      )}




    </div>
  );
}

// =============================================================================
// NoteEditor - floating popup
// =============================================================================
function NoteEditor({ popup, onSave, onCancel, onChange }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); }, []);

  const x = Math.min(Math.max((popup.x || 200) - 170, 8), window.innerWidth - 360);
  const y = Math.min(popup.y || 180, window.innerHeight - 220);

  return (
    <div className="note-popup-editor" style={{ position: 'fixed', left: x, top: y, zIndex: 450 }}>
      {popup.quote && (
        <div className="note-popup-quote">
          <span className="note-popup-quote-icon">❝</span>
          <span>{popup.quote.slice(0, 140)}{popup.quote.length > 140 ? '…' : ''}</span>
        </div>
      )}
      <textarea
        ref={ref}
        className="note-popup-input"
        value={popup.draft || ''}
        onChange={e => onChange(e.target.value)}
        placeholder="Write your note…"
        rows={3}
      />
      <div className="note-popup-actions">
        <button
          className="btn-note-save"
          onMouseDown={e => { e.preventDefault(); onSave(popup.draft || ''); }}
          disabled={!popup.draft?.trim()}
        >
          Save note
        </button>
        <button className="btn-note-cancel" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

// =============================================================================
// ParagraphBlock
// =============================================================================


function ParagraphBlock({
  paraIdx, text, annotations, highlights, notes,
  onAnnClick, onEditNote, onDeleteNote,
}) {
  const isHeading  = /^#{1,3}\s/.test(text);
  const isBullet   = text.startsWith('- ') || text.startsWith('• ');
  const calloutKey = Object.keys(CALLOUT_MAP).find(k => text.startsWith(k));
  const isLead     = /^\*\*[^*].+\*\*$/.test(text.trim());

  function renderInline(raw) {
    const plain = raw
      .replace(/^#{1,3}\s+/, '')
      .replace(/^\*\*(.+)\*\*$/, '$1')
      .replace(/\*\*(.*?)\*\*/g, '$1');

    // Collect all ranges: highlights + annotation underlines
    const ranges = [];

    highlights.forEach(h => {
      if (!h.text) return;
      // Use stored character offsets if this highlight belongs to this paragraph
      // - this is exact and never fails due to whitespace/span boundaries.
      if (h.paraIdx === paraIdx && h.startOffset >= 0 && h.endOffset > h.startOffset) {
        ranges.push({ start: h.startOffset, end: h.endOffset, type: 'hl', hl: h });
        return;
      }
      // Fallback: string search for highlights from other sources (e.g. loaded state)
      if (!h.text) return;
      const needle = h.text.replace(/\s+/g, ' ').trim();
      const haystack = plain.replace(/\s+/g, ' ');
      const idx = haystack.indexOf(needle);
      if (idx >= 0) {
        ranges.push({ start: idx, end: idx + needle.length, type: 'hl', hl: h });
      }
    });

    if (annotations?.length) {
      annotations.forEach(ann => {
        const esc = ann.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re  = new RegExp(`\\b${esc}\\b`, 'gi');
        let m;
        while ((m = re.exec(plain)) !== null) {
          ranges.push({ start: m.index, end: m.index + m[0].length, type: 'ann', ann, matched: m[0] });
        }
      });
    }

    // Sort: by start position; prefer 'hl' over 'ann' on ties
    ranges.sort((a, b) => a.start - b.start || (a.type === 'hl' ? -1 : 1));

    // Deduplicate overlapping ranges
    const deduped = [];
    let cursor = 0;
    for (const r of ranges) {
      if (r.start >= cursor) { deduped.push(r); cursor = r.end; }
    }

    const nodes = [];
    let pos = 0;

    for (const r of deduped) {
      if (r.start > pos) {
        const slice = plain.slice(pos, r.start).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        nodes.push(<span key={`t${pos}`} dangerouslySetInnerHTML={{ __html: slice }} />);
      }

      const slice = plain.slice(r.start, r.end);

      if (r.type === 'hl') {
        nodes.push(
          <mark key={`hl${r.start}`} style={{ background: r.hl.color, borderRadius: '3px', padding: '1px 2px' }}>
            {slice}
          </mark>
        );
      } else {
        const color = TYPE_COLORS[r.ann.type] || '#2563eb';
        nodes.push(
          <span
            key={`ann${r.start}`}
            className="annotated-term"
            style={{ borderBottomColor: color, '--ann-color': color }}
            onClick={e => onAnnClick(r.ann, e)}
            title={r.ann.short}
          >
            {r.matched}
          </span>
        );
      }
      pos = r.end;
    }

    if (pos < plain.length) {
      const slice = plain.slice(pos).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      nodes.push(<span key={`t${pos}`} dangerouslySetInnerHTML={{ __html: slice }} />);
    }

    return <>{nodes}</>;
  }

  return (
    <div className="para-block" data-para-idx={paraIdx}>
      <div className="para-content">
        {isHeading ? (
          <h2 className="doc-heading">{renderInline(text)}</h2>
        ) : calloutKey ? (
          <div className="callout callout--highlight">
            <span>{CALLOUT_MAP[calloutKey]}</span>
            <span>{renderInline(text)}</span>
          </div>
        ) : isBullet ? (
          <p className="doc-para doc-para--bullet">
            <span className="bullet-dot">·</span>{' '}
            {renderInline(text.replace(/^[-•]\s*/, ''))}
          </p>
        ) : isLead ? (
          <p className="doc-para doc-para--lead"><strong>{renderInline(text)}</strong></p>
        ) : (
          <p className="doc-para">{renderInline(text)}</p>
        )}
      </div>

      {/* Notes attached to this paragraph */}
      {notes.length > 0 && (
        <div className="para-notes-list">
          {notes.map(note => (
            <div key={note.id} className="para-note">
              {note.quote && (
                <blockquote className="para-note-quote">"{note.quote}"</blockquote>
              )}
              <div className="para-note-body">
                <span className="para-note-icon">📝</span>
                <span className="para-note-text">{note.text}</span>
              </div>
              <div className="para-note-actions">
                <button onClick={() => onEditNote(note)}>Edit</button>
                <button onClick={() => onDeleteNote(note.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// AnnotationPopup - shows when user clicks a highlighted concept in the text
// =============================================================================
const TYPE_LABELS = {
  concept:    { icon: '💡', label: 'Concept'    },
  formula:    { icon: '∑',  label: 'Formula'    },
  person:     { icon: '👤', label: 'Person'     },
  definition: { icon: '📖', label: 'Definition' },
};

function AnnotationPopup({ ann, pos, onClose }) {
  const color  = TYPE_COLORS[ann.type] || '#2563eb';
  const meta   = TYPE_LABELS[ann.type] || { icon: '💡', label: ann.type };

  // Keep popup inside viewport
  const [finalPos, setFinalPos] = React.useState(pos);
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const r  = ref.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    setFinalPos({
      x: Math.min(Math.max(pos.x, 12), vw - r.width  - 12),
      y: pos.y + r.height > vh - 12 ? pos.y - r.height - 14 : pos.y,
    });
  }, [pos.x, pos.y]);

  return (
    <div
      ref={ref}
      className="annotation-popup"
      style={{ left: finalPos.x, top: finalPos.y }}
    >
      {/* Header strip coloured by concept type */}
      <div className="ann-popup-header" style={{ borderLeftColor: color, background: `${color}12` }}>
        <span className="ann-popup-type-badge" style={{ background: `${color}22`, color }}>
          {meta.icon} {meta.label}
        </span>
        <span className="ann-popup-term">{ann.term}</span>
        <button className="ann-popup-close" onClick={onClose} aria-label="Close">×</button>
      </div>

      {/* Short one-line meaning */}
      <p className="ann-popup-short">{ann.short}</p>

      {/* Divider */}
      <div className="ann-popup-divider" />

      {/* Full explanation */}
      <p className="ann-popup-detail">{ann.detail}</p>
    </div>
  );
}

// =============================================================================
// PDF print helper
// =============================================================================
function buildPrintHtml(text, notes, highlights) {
  if (!text) return '';
  return text.split(/\n\s*\n/).filter(p => p.trim()).map((para, idx) => {
    let t = para.trim();
    highlights.forEach(h => {
      if (t.includes(h.text)) {
        const esc = h.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        t = t.replace(new RegExp(esc, 'g'), `<mark style="background:${h.color}">${h.text}</mark>`);
      }
    });
    t = t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    const paraNotesHtml = (notes[idx] || []).map(n => `
      <div class="note-block">
        ${n.quote ? `<div class="note-quote">❝ ${n.quote}</div>` : ''}
        <div>📝 ${n.text}</div>
      </div>`).join('');

    if (/^#{1,3}\s/.test(t)) return `<h2>${t.replace(/^#{1,3}\s+/, '')}</h2>${paraNotesHtml}`;
    const ck = Object.keys(CALLOUT_MAP).find(k => t.startsWith(k));
    if (ck) return `<div class="callout">${t}</div>${paraNotesHtml}`;
    return `<p>${t}</p>${paraNotesHtml}`;
  }).join('\n');
}