import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import NavBar from './components/NavBar';
import HomePage from './components/pages/HomePage';
import PublisherPage from './components/pages/PublisherPage'; // Import PublisherPage component
import AdvertiserPage from './components/pages/AdvertiserPage';
import AdUnitPage from './components/pages/AdUnitPage'; // Import AdUnitPage component
import CampaignPage from './components/pages/CampaignPage';
import AdPage from './components/pages/AdPage';
import Reports from './components/pages/Reports';


function App() {
  return (
    <Router>
      <div style={{ display: 'flex' }}>
        <NavBar />
        <div style={{ padding: '20px' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/inventory" element={<PublisherPage />} />
            <Route path="/demand" element={<AdvertiserPage />} />
            <Route path="/inventory/:PubId" element={<AdUnitPage />} />
            <Route path="/demand/:AdvId" element={<CampaignPage />} />
            <Route path='/demand/:AdvId/campaign/:CampId' element={<AdPage />} />
            <Route path="/report" element={<Reports />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
