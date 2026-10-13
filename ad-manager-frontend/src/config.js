// Service URLs, resolved at runtime.
//
// Vite inlines import.meta.env.VITE_* at *build* time, so a single image could not be promoted from stage to
// prod. The container's entrypoint writes config.js from its environment on startup instead (it still reads
// REACT_APP_API_BASE_URL and REACT_APP_API_AD_SERVER_URL, the names the Helm chart and Compose file already
// set). The VITE_* values remain the fallback for `npm run dev`.
const runtime = (typeof window !== 'undefined' && window.__ADPULSE_CONFIG__) || {};

function resolve(runtimeValue, buildTimeValue) {
  // The entrypoint leaves unset variables as an empty string.
  return runtimeValue || buildTimeValue || '';
}

export const API_BASE_URL = resolve(runtime.API_BASE_URL, import.meta.env.VITE_API_BASE_URL);
export const AD_SERVER_URL = resolve(runtime.AD_SERVER_URL, import.meta.env.VITE_API_AD_SERVER_URL);
