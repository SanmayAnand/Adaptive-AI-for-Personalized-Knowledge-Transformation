// src/components/Sidebar.js
import '../styles/sidebar.css';

const LEVEL_EMOJI = { beginner: '🌱', intermediate: '📖', expert: '⚡' };

export default function Sidebar({ history, currentFilename, onNewDoc, onOpenDoc }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <span className="brand-logo">A</span>
          <span className="brand-name">AKTE</span>
        </div>
        <button className="sidebar-new" onClick={onNewDoc}>
          <span>+</span> New document
        </button>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Recent</div>
        {history.length === 0 && (
          <div className="sidebar-empty">No documents yet</div>
        )}
        {history.map((doc, i) => {
          const isActive = doc.filename === currentFilename;
          return (
            <button
              key={i}
              className={`sidebar-item ${isActive ? 'sidebar-item--active' : ''}`}
              onClick={() => onOpenDoc(doc)}
              title={`Reopen ${doc.filename}`}
            >
              <span className="sidebar-item-emoji">
                {LEVEL_EMOJI[doc.level] || '📄'}
              </span>
              <div className="sidebar-item-info">
                <span className="sidebar-item-name">
                  {doc.filename.replace(/\.[^.]+$/, '')}
                </span>
                <span className="sidebar-item-level">{doc.level}</span>
              </div>
            </button>
          );
        })}
      </div>
    </nav>
  );
}