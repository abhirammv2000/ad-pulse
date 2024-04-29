import React, { useState, useEffect } from 'react';
import axios from 'axios';
import adServeRequestBody from '../requests/adServeRequest';

const AdPopup = ({ adUnitId, width, height, position }) => {
  const [imageUrl, setImageUrl] = useState('');
  const [clickUrl, setClickUrl] = useState('');
  const [landingUrl, setLandingUrl] = useState('');
  const [showAd, setShowAd] = useState(true);
  const adServeUrl = process.env.REACT_APP_API_AD_SERVER_URL;

  useEffect(() => {
    const fetchAdImage = async () => {
      try {
        const requestBody = { ...adServeRequestBody }; // Make a copy of the request body
        requestBody.imp[0].native.request.assets[0].img.w = width; // Set width
        requestBody.imp[0].native.request.assets[0].img.h = height; // Set height
        const response = await axios.post(`${adServeUrl}/adserve?adunit_id=${adUnitId}&publisher_id=P20240417203653208`, requestBody);
        const adm = JSON.parse(response.data.bid[0].adm);
        setImageUrl(adm.imageURL);
        setClickUrl(response.data.bid[0].ext.clickUrl);
        setLandingUrl(response.data.bid[0].ext.landingUrl);
        await axios.get(response.data.bid[0].ext.renderUrl);
      } catch (error) {
        console.error('Error fetching ad image:', error);
      }
    };

    fetchAdImage();
  }, [adServeUrl, adUnitId, width, height]);

  const handleClick = async () => {
    window.open(landingUrl.includes('http') ? landingUrl : `https://${landingUrl}`, '_blank');
    try {
      const response = await axios.get(clickUrl);
      console.log('Click URL:', response.data);
    } catch (error) {
      console.error('Error fetching click URL:', error);
    }
  };

  const handleClose = () => {
    setShowAd(false);
  };

  let containerWidth = 0;
  let containerHeight = 0;

  // Set container size based on aspect ratio of the image
  if (width > height) {
    containerWidth = 320;
    containerHeight = Math.round((height / width) * containerWidth);
  } else {
    containerHeight = 320;
    containerWidth = Math.round((width / height) * containerHeight);
  }

  let positionStyle = {};

  if (position === 'top') {
    positionStyle = { top: '20%', left: '50%', transform: 'translate(-50%, -50%)' };
  } else if (position === 'bottom') {
    positionStyle = { bottom: '20%', left: '50%', transform: 'translate(-50%, 50%)' };
  } else if (position === 'left') {
    positionStyle = { top: '50%', left: '10px', transform: 'translateY(-50%)' };
  } else if (position === 'right') {
    positionStyle = { top: '50%', right: '10%', transform: 'translateY(-50%)' };
  }

  const containerStyle = {
    position: 'fixed',
    ...positionStyle,
    width: `${containerWidth}px`,
    height: `${containerHeight}px`,
    backgroundColor: 'white',
    padding: '20px',
    border: '1px solid #ccc',
    borderRadius: '5px',
    overflow: 'hidden',
  };

  const imgStyle = {
    width: '100%',
    height: 'auto',
    cursor: 'pointer'
  };

  return (
    <>
      {showAd && imageUrl && (
        <div className="ad-popup" style={containerStyle}>
          <button style={{ position: 'absolute', top: '5px', right: '5px', cursor: 'pointer' }} onClick={handleClose}>X</button>
          {imageUrl && (
            <img
              src={imageUrl}
              alt="Advertisement"
              style={imgStyle}
              onClick={handleClick}
            />
          )}
        </div>
      )}
    </>
  );
};

export default AdPopup;
