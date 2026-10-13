// API key handling for calls to the ad manager.
//
// When the manager has API_KEY set it answers 401 to any request without a matching X-API-Key header. The
// dashboard cannot ship the key inside the page, because anyone who can load the page could read it, so the
// person using it types the key in. It is kept in sessionStorage, which is cleared when the tab closes.
//
// installAuth(axios) adds the header to every request and, when the manager answers 401, tells the page to ask
// for the key by dispatching AUTH_REQUIRED_EVENT. ApiKeyDialog listens for that event.

import { API_BASE_URL } from './config';

export const API_KEY_HEADER = 'X-API-Key';
export const AUTH_REQUIRED_EVENT = 'adpulse:auth-required';

const STORAGE_KEY = 'adpulse.apiKey';

export function getApiKey() {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) || '';
  } catch (error) {
    return ''; // storage can be blocked, for example in a private window
  }
}

export function setApiKey(key) {
  try {
    if (key) {
      window.sessionStorage.setItem(STORAGE_KEY, key);
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    // nothing to do: without storage the person is asked again after a reload
  }
}

function originOf(url) {
  try {
    return new URL(url).origin;
  } catch (error) {
    return null;
  }
}

// The key belongs to the ad manager and must never be sent anywhere else. The dashboard also calls the ad server,
// which has no keys, and only the manager's 401s mean "ask for the key". A relative URL goes to the dashboard's own
// origin, which is where the manager is when API_BASE_URL is empty. An absolute URL has to be on the manager's origin.
export function isManagerRequest(config) {
  const url = (config && config.url) || '';
  if (!/^https?:/i.test(url)) {
    return true;
  }
  const managerOrigin = originOf(API_BASE_URL);
  return managerOrigin !== null && originOf(url) === managerOrigin;
}

export function installAuth(client) {
  client.interceptors.request.use((config) => {
    const key = getApiKey();
    if (key && isManagerRequest(config)) {
      config.headers[API_KEY_HEADER] = key;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error && error.response && error.response.status === 401 && isManagerRequest(error.config)) {
        window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
      }
      return Promise.reject(error);
    }
  );
}
