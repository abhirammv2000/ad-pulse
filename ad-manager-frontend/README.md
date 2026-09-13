# ad-manager-frontend

React dashboard for ad-manager-svc — managing publishers, ad units,
advertisers, campaigns, ads and creatives — plus a demo homepage that requests
a live ad from ad-server-svc and renders it.

## Configuration

Two service URLs, resolved in `src/config.js`:

| Variable | Purpose |
|---|---|
| `REACT_APP_API_BASE_URL` | ad-manager-svc base URL |
| `REACT_APP_API_AD_SERVER_URL` | ad-server-svc base URL |

`npm start` reads these the normal Create React App way (a `.env` file or the
shell environment at build time). The production image is different: Create
React App inlines `REACT_APP_*` at *build* time, which would mean rebuilding
the image for every environment, so the built bundle instead reads
`window.__ADPULSE_CONFIG__` — written to `public/config.js` by the container's
entrypoint (`docker-entrypoint.sh`) from its own environment at container
startup. One image can be promoted from stage to prod unmodified.

## Running

```
npm ci
REACT_APP_API_BASE_URL=http://localhost:5000 \
REACT_APP_API_AD_SERVER_URL=http://localhost:8080 \
npm start
```

## Testing

```
npm test           # component tests
npm run test:e2e   # Selenium smoke test against a running app (frontend-test.js)
```

## Building the production image

```
docker build -t ad-manager-frontend .
docker run -p 3000:3000 \
  -e REACT_APP_API_BASE_URL=https://api.example.com \
  -e REACT_APP_API_AD_SERVER_URL=https://ads.example.com \
  ad-manager-frontend
```
