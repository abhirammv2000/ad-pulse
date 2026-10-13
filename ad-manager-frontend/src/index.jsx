import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import axios from 'axios';
import App from './App';
import { installAuth } from './auth';

// Adds the manager's API key to requests and asks for it when the manager answers 401. See auth.js.
installAuth(axios);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
