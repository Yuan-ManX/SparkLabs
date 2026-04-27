import React, { useState } from 'react';
import SparkLabsHome from './components/SparkLabsHome';
import SparkLabsEditor from './components/SparkLabsEditor';

function App() {
  const [isOnLandingPage, setIsOnLandingPage] = useState(true);

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
