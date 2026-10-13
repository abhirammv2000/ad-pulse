// Opens the built dashboard in a real browser and walks through what the unit tests cannot see: the production
// bundle loading, the runtime config.js, the API key dialog, and where the key is (and is not) sent.
//
// It needs a running stack whose manager has API_KEY=local-dev-api-key (the Compose file in ad-devops does), and
// `playwright` installed where this file runs. CI does that in a scratch folder. See ad-manager-frontend/README.md.
//
//   DASHBOARD_URL, MANAGER_URL, AD_SERVER_URL  where each service is, as the browser reaches it
//   API_KEY                                    the manager's key
import { chromium } from 'playwright';

const base = process.env.DASHBOARD_URL || 'http://localhost:3000';
const manager = process.env.MANAGER_URL || 'http://localhost:5000';
const adServer = process.env.AD_SERVER_URL || 'http://localhost:8080';
const apiKey = process.env.API_KEY || 'local-dev-api-key';

const results = [];
function check(name, ok, detail = '') {
  results.push(ok);
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`);
}

const browser = await chromium.launch();
const page = await browser.newPage();

const pageErrors = [];
page.on('pageerror', (e) => pageErrors.push(e.message));

const sent = []; // { url, key }
page.on('request', (req) => {
  if (req.url().startsWith(manager) || req.url().startsWith(adServer)) {
    sent.push({ url: req.url(), method: req.method(), key: req.headers()['x-api-key'] });
  }
});

try {
  // 1. The app loads and reads the runtime config.js (the URLs above are only known to it from there).
  await page.goto(base + '/');
  await page.getByText('Welcome to Ad Pulse').waitFor({ timeout: 15000 });
  check('home page renders', true);
  const cfg = await page.evaluate(() => window.__ADPULSE_CONFIG__);
  check('runtime config.js was read', cfg && cfg.API_BASE_URL === manager, JSON.stringify(cfg));

  // 2. A deep link works (nginx falls back to index.html) and the manager's 401 opens the key dialog.
  await page.goto(base + '/inventory');
  await page.getByText('API key needed').waitFor({ timeout: 15000 });
  check('deep link /inventory loads and the key dialog opens on 401', true);
  check('Continue is disabled with no key', await page.getByRole('button', { name: 'Continue' }).isDisabled());

  // 3. A wrong key reloads the page and the dialog comes back.
  await page.getByRole('dialog').locator('input').fill('wrong-key');
  await Promise.all([page.waitForEvent('load'), page.getByRole('button', { name: 'Continue' }).click()]);
  await page.getByText('API key needed').waitFor({ timeout: 15000 });
  check('a wrong key brings the dialog back', true);

  // 4. The right key lets the table load.
  await page.getByRole('dialog').locator('input').fill(apiKey);
  await Promise.all([page.waitForEvent('load'), page.getByRole('button', { name: 'Continue' }).click()]);
  await page.getByRole('columnheader', { name: 'Publisher ID' }).waitFor({ timeout: 15000 });
  check('the right key loads the publishers table', true);
  const dialogGone = (await page.getByText('API key needed').count()) === 0;
  check('the dialog is gone', dialogGone);
  check('Add new publisher button is shown', await page.getByRole('button', { name: /Add new publisher/i }).isVisible());

  // 5. Client-side navigation to the other tables.
  await page.getByText('Demand', { exact: true }).click();
  await page.getByRole('columnheader', { name: 'Advertiser ID' }).waitFor({ timeout: 15000 });
  check('Demand page loads through the router', true);

  // 6. Back on the home page, which asks the ad server for an ad.
  await page.goto(base + '/');
  await page.getByText('Welcome to Ad Pulse').waitFor({ timeout: 15000 });
  await page.waitForTimeout(2000);

  // 7. Where the key went.
  const toManagerWithKey = sent.filter((r) => r.url.startsWith(manager) && r.key === apiKey);
  const toAdServer = sent.filter((r) => r.url.startsWith(adServer));
  const adServerWithKey = toAdServer.filter((r) => r.key);
  check('requests to the manager carried the key', toManagerWithKey.length > 0, `${toManagerWithKey.length} requests`);
  check('the browser did call the ad server', toAdServer.length > 0, `${toAdServer.length} requests`);
  check('no request to the ad server carried the key', adServerWithKey.length === 0, `${adServerWithKey.length} did`);

  // 8. Script errors.
  check('no uncaught script errors', pageErrors.length === 0, pageErrors.join(' | '));
} catch (err) {
  check('browser check ran to the end', false, String(err).split('\n')[0]);
  await page.screenshot({ path: process.env.SMOKE_SCREENSHOT || 'smoke-failure.png' }).catch(() => {});
} finally {
  await browser.close();
}

const failed = results.filter((ok) => !ok).length;
console.log(failed === 0 ? `\nall ${results.length} checks passed` : `\n${failed} of ${results.length} checks FAILED`);
process.exit(failed === 0 ? 0 : 1);
