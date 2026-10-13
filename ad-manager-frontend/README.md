# ad-manager-frontend

React dashboard for ad-manager-svc: managing publishers, ad units,
advertisers, campaigns, ads and creatives, plus a demo homepage that requests
a live ad from ad-server-svc and renders it. It is built with Vite and tested
with Vitest. Use Node 24, which is what the image and CI use.

## Configuration

Two service URLs, resolved in `src/config.js`:

| Purpose | In the container | With `npm run dev` |
|---|---|---|
| ad-manager-svc base URL | `REACT_APP_API_BASE_URL` | `VITE_API_BASE_URL` |
| ad-server-svc base URL | `REACT_APP_API_AD_SERVER_URL` | `VITE_API_AD_SERVER_URL` |

The container reads the `REACT_APP_*` names because the Helm chart and the
Compose file already set them, even though the build tool is no longer Create
React App. Vite inlines `VITE_*` values at *build* time, which would mean
rebuilding the image for every environment. So the built bundle instead reads
`window.__ADPULSE_CONFIG__`, written to `config.js` by the container's
entrypoint (`docker-entrypoint.sh`) from its own environment at container
startup. One image can be promoted from stage to prod unmodified. `npm run dev`
uses the `VITE_*` values (a `.env` file or the shell environment).

If the manager has an `API_KEY`, the dashboard asks for it the first time it
gets a 401 and keeps it in `sessionStorage` for that tab. See `src/auth.js`.

## Running

```
npm ci
VITE_API_BASE_URL=http://localhost:5000 \
VITE_API_AD_SERVER_URL=http://localhost:8080 \
npm run dev
```

The dev server is on http://localhost:3000.

## Testing

```
npm test              # runs every component test once
npm run test:watch    # reruns the tests as files change
```

The component tests run in jsdom, which cannot show whether the production bundle
really loads. `smoke/smoke.mjs` does that in Chromium against a running stack: it
opens the built dashboard, goes through the API key dialog, and checks that the key
is sent to the manager and never to the ad server. CI runs it after the integration
test. To run it yourself, start the Compose stack from the repository root and then:

```
mkdir /tmp/smoke && cp smoke/smoke.mjs /tmp/smoke && cd /tmp/smoke
npm init -y && npm install playwright@1.64.0 && npx playwright install chromium
node smoke.mjs
```

## Building the production image

```
docker build -t ad-manager-frontend .
docker run -p 3000:3000 \
  -e REACT_APP_API_BASE_URL=https://api.example.com \
  -e REACT_APP_API_AD_SERVER_URL=https://ads.example.com \
  ad-manager-frontend
```
