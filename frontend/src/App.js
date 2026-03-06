// =============================================================================
// src/App.js  —  root component, owns all global state
// =============================================================================
import { useState, useCallback } from 'react';
import Upload    from './components/Upload';
import Quiz      from './components/Quiz';
import LevelResult from './components/LevelResult';
import StudyView from './components/StudyView';
import Sidebar   from './components/Sidebar';
import './styles/app.css';

// Generate a persistent user_id for this session.
// In production you'd use real auth. For the hackathon, localStorage is fine.
function getOrCreateUserId() {
  const key = 'akte_user_id';
  let id = localStorage.getItem(key);
  if (!id) {
    id = 'user_' + Math.random().toString(36).slice(2, 12);
    localStorage.setItem(key, id);
  }
  return id;
}

const USER_ID = getOrCreateUserId();

// Page states: upload → quiz → level → study
// The sidebar is always visible once the user has at least one document.
export default function App() {
  const [page, setPage] = useState('upload');

  // Upload step
  const [uploadData, setUploadData] = useState(null);
  // { filename (sanitised), docId, contentType }

  // Quiz step
  const [quizData, setQuizData] = useState(null);
  // { mcqQuestions, selfQuestions, wordCount, extractionNote }

  // After quiz scoring
  const [scoreData, setScoreData] = useState(null);
  // { score, level, intent, docId }

  // After transform
  const [studyData, setStudyData] = useState(null);
  // { downloadUrl, level, intent, annotations, originalText, transformedText, filename }

  // Sidebar doc history (could be fetched from quiz_handler action='history')
  const [docHistory, setDocHistory] = useState([]);

  const handleUploadDone = useCallback((data) => {
    // data = { filename, docId }
    setUploadData(data);
    setPage('quiz');
  }, []);

  const handleQuizLoaded = useCallback((data) => {
    setQuizData(data);
  }, []);

  const handleScored = useCallback((data) => {
    // data = { score, level, intent, doc_id }
    setScoreData(data);
    setPage('level');
  }, []);

  const handleTransformDone = useCallback((data) => {
    // data = { downloadUrl, level, intent, annotations, originalText, transformedText, filename }
    setStudyData(data);
    // Add to sidebar history
    setDocHistory(prev => [{
      filename: data.filename,
      level: data.level,
      docId: scoreData?.doc_id,
      at: new Date().toISOString(),
    }, ...prev]);
    setPage('study');
  }, [scoreData]);

  const handleNewDoc = useCallback(() => {
    setUploadData(null);
    setQuizData(null);
    setScoreData(null);
    setStudyData(null);
    setPage('upload');
  }, []);

  const showSidebar = docHistory.length > 0 || page === 'study';

  return (
    <div className={`app-shell ${showSidebar ? 'has-sidebar' : ''}`}>
      {showSidebar && (
        <Sidebar
          userId={USER_ID}
          history={docHistory}
          currentPage={page}
          onNewDoc={handleNewDoc}
        />
      )}

      <main className="app-main">
        {page === 'upload' && (
          <Upload
            userId={USER_ID}
            onDone={handleUploadDone}
            onQuizLoaded={handleQuizLoaded}
          />
        )}

        {page === 'quiz' && uploadData && (
          <Quiz
            userId={USER_ID}
            filename={uploadData.filename}
            docId={uploadData.docId}
            quizData={quizData}
            onScored={handleScored}
          />
        )}

        {page === 'level' && scoreData && (
          <LevelResult
            userId={USER_ID}
            filename={uploadData?.filename}
            docId={scoreData.doc_id}
            scoreData={scoreData}
            onTransformDone={handleTransformDone}
          />
        )}

        {page === 'study' && studyData && (
          <StudyView
            data={studyData}
            onNewDoc={handleNewDoc}
          />
        )}
      </main>
    </div>
  );
}