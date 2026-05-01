import React, { useState, useEffect } from 'react';
import SparkLabsHome from './components/SparkLabsHome';
import SparkLabsEditor from './components/SparkLabsEditor';

function App() {
  const [isOnLandingPage, setIsOnLandingPage] = useState(() => {
    const path = window.location.pathname;
    return !path.includes('/Editor');
  });

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      setIsOnLandingPage(!path.includes('/Editor'));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const enterEditor = () => {
    window.history.pushState({}, '', '/SparkLabs/Editor');
    setIsOnLandingPage(false);
  };

  const goHome = () => {
    window.history.pushState({}, '', '/SparkLabs/Editor');
    setIsOnLandingPage(true);
  };

  if (isOnLandingPage) {
    return (
      <div className="min-h-screen">
        <SparkLabsHome onEnterEditor={enterEditor} />
      </div>
    );
  }

  return <SparkLabsEditor onGoHome={goHome} />;
}

export default App;
