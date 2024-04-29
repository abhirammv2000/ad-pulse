import React from 'react';
import AdPopUp from '../AdPopUp';

const HomePage = () => {
  return (
    <div>
      <h1>Welcome to Ad Pulse</h1>
      <p>This is the homepage of Ad Pulse. You can navigate through the navbar.</p>
      <AdPopUp adUnitId="ADU20240417203820766" width={1280} height={720} position="bottom"/>
      <AdPopUp adUnitId="ADU20240425230346352" width={1280} height={720} position="top"/>
      <AdPopUp adUnitId="ADU20240425222446949" width={320} height={800} position="right"/>
    </div>
  );
};

export default HomePage;