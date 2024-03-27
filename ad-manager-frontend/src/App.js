import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import NavBar from './components/NavBar';
import HomePage from './components/pages/HomePage';
import PublisherPage from './components/pages/PublisherList'; // Import PublisherPage component

function App() {
  return (
    <Router>
      <div style={{ display: 'flex' }}>
        <NavBar />
        <div style={{ marginLeft: '240px', padding: '20px' }}> {/* Adjust marginLeft to match NavBar width */}
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/inventory/publisher" element={<PublisherPage />} /> {/* Add route for PublisherPage */}
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
