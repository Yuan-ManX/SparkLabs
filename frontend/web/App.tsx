import React, { useState, useEffect } from 'react';
import SparkLabsHome from './components/SparkLabsHome';
import SparkLabsEditor from './components/SparkLabsEditor';

function App() {
  const [isOnLandingPage, setIsOnLandingPage] = useState(() => {
    return !window.location.pathname.endsWith('/editor');
  });

  useEffect(() => {
    const handlePopState = () => {
      setIsOnLandingPage(!window.location.pathname.endsWith('/editor'));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const enterEditor = () => {
    window.history.pushState({}, '', '/sparklabs/editor');
    setIsOnLandingPage(false);
  };

  const goHome = () => {
    window.history.pushState({}, '', '/sparklabs');
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
