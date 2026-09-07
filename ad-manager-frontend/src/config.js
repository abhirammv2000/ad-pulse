// Service URLs, resolved at runtime.
//
// Create React App inlines process.env.REACT_APP_* at *build* time, so a single
// image could not be promoted from stage to prod. The container's entrypoint
// writes public/config.js from its environment on startup instead; the
// REACT_APP_* values remain the fallback for `npm start` during development.
const runtime = (typeof window !== 'undefined' && window.__ADPULSE_CONFIG__) || {};

function resolve(runtimeValue, buildTimeValue) {
  // The entrypoint leaves unset variables as an empty string.
  return runtimeValue || buildTimeValue || '';
}

export const API_BASE_URL = resolve(runtime.API_BASE_URL, process.env.REACT_APP_API_BASE_URL);
export const AD_SERVER_URL = resolve(runtime.AD_SERVER_URL, process.env.REACT_APP_API_AD_SERVER_URL);
