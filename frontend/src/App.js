// =============================================================================
// src/App.js  —  root component, owns all global state
// =============================================================================
import { useState, useCallback } from 'react';
import Upload      from './components/Upload';
import Quiz        from './components/Quiz';
import LevelResult from './components/LevelResult';
import StudyView   from './components/StudyView';
import Sidebar     from './components/Sidebar';
import './styles/app.css';

function getOrCreateUserId() {
  const key = 'akte_user_id';
  let id = localStorage.getItem(key);
  if (!id) {
    id = 'user-' + Math.random().toString(36).replace(/[^a-z0-9]/g, '').slice(0, 10);
    localStorage.setItem(key, id);
  }
  return id;
}

const USER_ID = getOrCreateUserId();

// Restore study session if returning from the game page
function getInitialState() {
  try {
    const saved = sessionStorage.getItem('AKTE_STUDY_RESTORE');
    if (saved) {
      sessionStorage.removeItem('AKTE_STUDY_RESTORE');
      const { studyData, docHistory } = JSON.parse(saved);
      if (studyData) return { page: 'study', studyData, docHistory: docHistory || [studyData] };
    }
  } catch(e) {}
  return { page: 'upload', studyData: null, docHistory: [] };
}

const _init = getInitialState();

export default function App() {
  const [page,       setPage]       = useState(_init.page);
  const [uploadData, setUploadData] = useState(null);
  const [quizData,   setQuizData]   = useState(null);
  const [scoreData,  setScoreData]  = useState(null);
  const [studyData,  setStudyData]  = useState(_init.studyData);

  // docHistory stores full studyData per doc so clicking reopens the study view
  const [docHistory, setDocHistory] = useState(_init.docHistory);

  const handleUploadDone = useCallback((data) => {
    setUploadData(data);
    setPage('quiz');
  }, []);

  const handleQuizLoaded = useCallback((data) => {
    setQuizData(data);
  }, []);

  const handleScored = useCallback((data) => {
    setScoreData(data);
    setPage('level');
  }, []);

  const handleTransformDone = useCallback((data) => {
    setStudyData(data);
    // Store full studyData — replace if same filename already exists, else prepend
    setDocHistory(prev => {
      const filtered = prev.filter(d => d.filename !== data.filename);
      return [data, ...filtered];
    });
    setPage('study');
  }, []);

  const handleNewDoc = useCallback(() => {
    setUploadData(null);
    setQuizData(null);
    setScoreData(null);
    setStudyData(null);
    setPage('upload');
  }, []);

  // Return to current study doc (e.g. after game)
  const handleBackToDoc = useCallback(() => {
    if (studyData) setPage('study');
  }, [studyData]);

  // Clicking a recent doc in the sidebar reopens its study view
  const handleOpenDoc = useCallback((savedStudyData) => {
    setStudyData(savedStudyData);
    setPage('study');
  }, []);

  const showSidebar = docHistory.length > 0 || page === 'study';

  return (
    <div className={`app-shell ${showSidebar ? 'has-sidebar' : ''}`}>
      {showSidebar && (
        <Sidebar
          userId={USER_ID}
          history={docHistory}
          currentPage={page}
          currentFilename={studyData?.filename}
          onNewDoc={handleNewDoc}
          onOpenDoc={handleOpenDoc}
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
            docHistory={docHistory}
            onNewDoc={handleNewDoc}
            onBackToDoc={handleBackToDoc}
          />
        )}
      </main>
    </div>
  );
}