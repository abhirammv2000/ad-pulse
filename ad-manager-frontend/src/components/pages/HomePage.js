import React, { useState, useEffect } from 'react';
import axios from 'axios';
import adServeRequestBody from '../../requests/adServeRequest';
import { AD_SERVER_URL } from '../../config';

// The demo publisher whose ad units the homepage renders.
const DEMO_PUBLISHER_ID = 'P20240417203653208';

const POSITION_STYLES = {
  bottom: { bottom: 0, left: '50%', transform: 'translateX(-50%)', marginBottom: '20px' },
  top: { top: 0, left: '50%', transform: 'translateX(-50%)', marginTop: '20px' },
  right: { top: '50%', right: 0, transform: 'translateY(-50%)', marginRight: '20px' },
};

const HomePage = () => (
  <div>
    <h1>Welcome to Ad Pulse</h1>
    <p>This is the homepage of Ad Pulse. You can navigate through the navbar.</p>
    <AdPopUp adUnitId="ADU20240417203820766" width={1280} height={720} position="bottom" />
    <AdPopUp adUnitId="ADU20240425230346352" width={1280} height={720} position="top" />
    <AdPopUp adUnitId="ADU20240425222446949" width={320} height={800} position="right" />
  </div>
);

/**
 * Requests one ad for an ad unit and renders the returned image.
 *
 * Clicking through and rendering both report back to the engagement service via
 * the tracking URLs the ad server hands out with the bid.
 */
function AdPopUp({ adUnitId, width, height, position, publisherId = DEMO_PUBLISHER_ID }) {
  const [imageUrl, setImageUrl] = useState('');
  const [clickUrl, setClickUrl] = useState('');
  const [landingUrl, setLandingUrl] = useState('');

  useEffect(() => {
    let cancelled = false;

    const fetchAdImage = async () => {
      try {
        // adServeRequestBody is a shared module object, so copy it before
        // setting this slot's dimensions; mutating it would let whichever
        // AdPopUp rendered last decide the size for all of them.
        const requestBody = {
          ...adServeRequestBody,
          imp: [{
            ...adServeRequestBody.imp[0],
            native: {
              ...adServeRequestBody.imp[0].native,
              request: {
                ...adServeRequestBody.imp[0].native.request,
                assets: [{
                  ...adServeRequestBody.imp[0].native.request.assets[0],
                  img: { ...adServeRequestBody.imp[0].native.request.assets[0].img, w: width, h: height },
                }],
              },
            },
          }],
        };

        const response = await axios.post(
          `${AD_SERVER_URL}/adserve?adunit_id=${adUnitId}&publisher_id=${publisherId}`,
          requestBody,
        );

        // A 204 means no bid: nothing to render.
        if (cancelled || !response.data || !response.data.bid || response.data.bid.length === 0) {
          return;
        }

        const [bid] = response.data.bid;
        setImageUrl(JSON.parse(bid.adm).imageURL);
        setClickUrl(bid.ext.clickUrl);
        setLandingUrl(bid.ext.landingUrl);
        await axios.get(bid.ext.renderUrl);
      } catch (error) {
        console.error(`Error fetching ad for ${adUnitId}:`, error);
      }
    };

    fetchAdImage();
    return () => {
      cancelled = true;
    };
  }, [adUnitId, publisherId, width, height]);

  const handleClick = async () => {
    if (landingUrl) {
      window.open(landingUrl.startsWith('http') ? landingUrl : `https://${landingUrl}`, '_blank', 'noopener');
    }
    try {
      await axios.get(clickUrl);
    } catch (error) {
      console.error('Error reporting click:', error);
    }
  };

  if (!imageUrl) {
    return null;
  }

  return (
    <div
      className="image-container"
      style={{ position: 'fixed', maxWidth: '320px', maxHeight: '180px', ...POSITION_STYLES[position] }}
    >
      <img
        src={imageUrl}
        alt="Advertisement"
        style={{ maxWidth: '100%', maxHeight: '100%', width: 'auto', height: 'auto', cursor: 'pointer' }}
        onClick={handleClick}
      />
    </div>
  );
}

export default HomePage;
