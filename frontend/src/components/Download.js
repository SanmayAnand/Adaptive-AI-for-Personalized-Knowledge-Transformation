// =============================================================================
// src/components/Download.js
// WHO WRITES THIS: Person D
// WHAT THIS IS: Screen 4 — shows the download link for the personalised document
// =============================================================================
//
// PROPS:
//   data     — { download_url: 'https://s3.presigned.url...' }
//   onReset  — function, called when user clicks "Transform Another Document"
//              App.js will go back to the Upload screen
//
// NO STATE NEEDED — this is a pure display screen.
//
// NOTE ABOUT THE DOWNLOAD URL:
//   It's a pre-signed S3 URL. It expires after 60 minutes.
//   Show a small note warning the user about this.
//
// JSX TO BUILD:
//   <div className="screen">
//     <div className="card success-card">
//       <div className="big-tick">✓</div>
//       <h2>Your Personalised Document is Ready!</h2>
//       <p>The document has been rewritten to match your knowledge level.</p>
//       <p style={{ fontSize: '13px', color: '#888' }}>⚠️ This download link expires in 60 minutes.</p>
//       <a href={data.download_url} download className="btn">
//         Download Document
//       </a>
//     </div>
//     <button className="btn-sec" onClick={onReset}>
//       Transform Another Document
//     </button>
//   </div>
//
// =============================================================================

export default function Download({ data, onReset }) {
  // TODO: implement this — full guide above
}
