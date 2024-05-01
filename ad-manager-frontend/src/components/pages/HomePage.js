// HomePage.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import adServeRequestBody from '../../requests/adServeRequest'; 

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

function ImageContainer() {
  const [imageUrl, setImageUrl] = useState('');
  const [clickUrl, setClickUrl] = useState('');
  const [landingUrl, setLandingUrl] = useState('');
  const adServeUrl = process.env.REACT_APP_API_AD_SERVER_URL;

  useEffect(() => {
    const fetchAdImage = async () => {
      try {
        adServeRequestBody.imp[0].native.request.assets[0].img.w = 1280; // Update the image width
        adServeRequestBody.imp[0].native.request.assets[0].img.h = 720; // Update the image height
        const response = await axios.post(`${adServeUrl}/adserve?adunit_id=ADU20240417203820766&publisher_id=P20240417203653208`, adServeRequestBody);
        const adm = JSON.parse(response.data.bid[0].adm);
        console.log('Ad image URL:', adm.imageURL);
        setImageUrl(adm.imageURL);
        setClickUrl(response.data.bid[0].ext.clickUrl);
        setLandingUrl(response.data.bid[0].ext.landingUrl);
        await axios.get(response.data.bid[0].ext.renderUrl);
      } catch (error) {
        console.error('Error fetching ad image:', error);
      }
    };

    fetchAdImage();
  }, [adServeUrl]); // Trigger the effect when adServeUrl changes

  const handleClick = async () => {
    window.open(landingUrl.includes('http') ? landingUrl : `https://${landingUrl}`, '_blank');
    try {
      const response = await axios.get(clickUrl);
      console.log('Click URL:', response.data);
    } catch (error) {
      console.error('Error fetching click URL:', error);
    }
  };

  return (
    <div className="image-container" style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', maxWidth: '320px', maxHeight: '180px', marginBottom: '20px' }}>
      {imageUrl && (
        <img 
          src={imageUrl} 
          alt="Advertisement" 
          style={{ 
            maxWidth: '100%', 
            maxHeight: '100%', 
            width: 'auto', 
            height: 'auto' 
          }}
          onClick={handleClick}
        />
      )}
    </div>
  );
}

export default HomePage;