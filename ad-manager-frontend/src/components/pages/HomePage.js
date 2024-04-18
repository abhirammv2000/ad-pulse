// HomePage.js
import React from 'react';
import axios from 'axios';

const HomePage = () => {
  return (
    <div>
      <h1>Welcome to Ad Pulse</h1>
      <p>This is the homepage of Ad Pulse. You can navigate through the navbar.</p>
      <ImageContainer />
    </div>
  );
};

function ImageContainer() {

  const handleClick = () => {
      // Send POST request using Axios
      axios.post('http://0.0.0.0:8080/adserve?adunit_id=ADU20240417203820766&publisher_id=P20240417203653208' , {
          // Add any data you want to send in the request body
      })
      .then(response => {
          // Handle successful response
          console.log(response.data);
      })
      .catch(error => {
          // Handle error
          console.error('Error:', error);
      });
  };

  return (
      <div className="image-container">
          <img 
              src="https://ads-static-testing.phonepe.com/cdn-cgi/image/width=1080,height=608/creatives/static/img/BA2402151719543396046214/2:15:18:47:36/__1440x810/en.png" 
              alt="Description of the image" 
              style={{ 
                  maxWidth: '1000px', 
                  maxHeight: '300px', 
                  width: 'auto', 
                  height: 'auto', 
                  position: 'absolute', 
                  bottom: '0', 
                  left: '50%', 
                  transform: 'translateX(-50%)' 
              }}
              onClick={handleClick} // Attach onClick event handler
          />
      </div>
  );
}

export default HomePage;