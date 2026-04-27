import React, { useState, useEffect } from 'react';
import SparkLabsHome from './components/SparkLabsHome';
import SparkLabsEditor from './components/SparkLabsEditor';

function App() {
  const [isOnLandingPage, setIsOnLandingPage] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('mode') !== 'editor';
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mode') === 'editor') {
      setIsOnLandingPage(false);
    }
  }, []);

  if (isOnLandingPage) {
    return (
      <div className="min-h-screen">
        <SparkLabsHome onEnterEditor={() => setIsOnLandingPage(false)} />
      </div>
    );
  }

  return <SparkLabsEditor />;
}

export default App;
