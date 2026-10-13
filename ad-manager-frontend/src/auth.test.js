import axios from 'axios';
import {
  API_KEY_HEADER,
  AUTH_REQUIRED_EVENT,
  getApiKey,
  installAuth,
  isManagerRequest,
  setApiKey,
} from './auth';

// The tests use a real axios instance with a fake adapter, so what is checked is the header axios would really
// send, not a mock of it.
jest.mock('./config', () => ({ API_BASE_URL: 'http://manager:5000' }));

const MANAGER = 'http://manager:5000';

function clientAnswering(status) {
  const sent = [];
  const client = axios.create({
    adapter: (config) => {
      sent.push(config);
      const response = { data: {}, status, statusText: '', headers: {}, config };
      if (status >= 200 && status < 300) {
        return Promise.resolve(response);
      }
      return Promise.reject(new axios.AxiosError('failed', 'ERR_BAD_REQUEST', config, null, response));
    },
  });
  installAuth(client);
  return { client, sent };
}

function headerSent(config) {
  return config.headers[API_KEY_HEADER] || config.headers.get(API_KEY_HEADER);
}

beforeEach(() => {
  window.sessionStorage.clear();
});

describe('storing the key', () => {
  test('a stored key is read back and can be cleared', () => {
    expect(getApiKey()).toBe('');
    setApiKey('abc');
    expect(getApiKey()).toBe('abc');
    setApiKey('');
    expect(getApiKey()).toBe('');
  });

  test('blocked storage does not break the page', () => {
    const getItem = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    const setItem = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(getApiKey()).toBe('');
    expect(() => setApiKey('abc')).not.toThrow();
    getItem.mockRestore();
    setItem.mockRestore();
  });
});

describe('which requests are the manager\'s', () => {
  test.each([
    [`${MANAGER}/ad`, true],
    [`${MANAGER}/creative/upload?filename=a.png`, true],
    ['/ad', true],
    ['http://ad-server:8080/adserve', false],
    ['http://manager:50001/ad', false], // a longer port is not the same origin
    ['https://manager:5000/ad', false], // another scheme is not the same origin
    ['http://manager.evil.example/ad', false],
  ])('%s -> %s', (url, expected) => {
    expect(isManagerRequest({ url })).toBe(expected);
  });
});

describe('sending the key', () => {
  test('a stored key goes on requests to the manager', async () => {
    setApiKey('secret');
    const { client, sent } = clientAnswering(200);
    await client.get(`${MANAGER}/publisher`);
    expect(headerSent(sent[0])).toBe('secret');
  });

  test('without a key no header is sent', async () => {
    const { client, sent } = clientAnswering(200);
    await client.get(`${MANAGER}/publisher`);
    expect(headerSent(sent[0])).toBeFalsy();
  });

  test('the key is never sent to another origin, such as the ad server', async () => {
    setApiKey('secret');
    const { client, sent } = clientAnswering(200);
    await client.post('http://ad-server:8080/adserve', {});
    expect(headerSent(sent[0])).toBeFalsy();
  });

  test('every method carries the key', async () => {
    setApiKey('secret');
    const { client, sent } = clientAnswering(200);
    await client.get(`${MANAGER}/a`);
    await client.post(`${MANAGER}/b`, {});
    await client.put(`${MANAGER}/c`, {});
    await client.patch(`${MANAGER}/d`);
    expect(sent.map(headerSent)).toEqual(['secret', 'secret', 'secret', 'secret']);
  });
});

describe('a 401 from the manager', () => {
  let onAuthRequired;

  beforeEach(() => {
    onAuthRequired = jest.fn();
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
  });

  afterEach(() => {
    window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
  });

  test('asks the page for the key and still rejects the call', async () => {
    const { client } = clientAnswering(401);
    await expect(client.get(`${MANAGER}/publisher`)).rejects.toMatchObject({ response: { status: 401 } });
    expect(onAuthRequired).toHaveBeenCalledTimes(1);
  });

  test('other errors do not ask for a key', async () => {
    for (const status of [400, 403, 404, 500]) {
      const { client } = clientAnswering(status);
      await expect(client.get(`${MANAGER}/publisher`)).rejects.toBeTruthy();
    }
    expect(onAuthRequired).not.toHaveBeenCalled();
  });

  test('a 401 from some other service does not ask for a key', async () => {
    const { client } = clientAnswering(401);
    await expect(client.get('http://ad-server:8080/adserve')).rejects.toBeTruthy();
    expect(onAuthRequired).not.toHaveBeenCalled();
  });

  test('a success does not ask for a key', async () => {
    const { client } = clientAnswering(200);
    await client.get(`${MANAGER}/publisher`);
    expect(onAuthRequired).not.toHaveBeenCalled();
  });
});
