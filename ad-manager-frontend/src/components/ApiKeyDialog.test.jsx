import { act, fireEvent, render, screen } from '@testing-library/react';
import ApiKeyDialog from './ApiKeyDialog';
import { AUTH_REQUIRED_EVENT, getApiKey, setApiKey } from '../auth';

const realLocation = window.location;

beforeEach(() => {
  window.sessionStorage.clear();
  delete window.location;
  window.location = { ...realLocation, reload: vi.fn() };
});

afterEach(() => {
  window.location = realLocation;
});

function askForKey() {
  act(() => {
    window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
  });
}

test('stays closed until the manager asks for a key', () => {
  render(<ApiKeyDialog />);
  expect(screen.queryByText('API key needed')).not.toBeInTheDocument();
});

test('opens when the manager asks, and cannot be submitted empty', () => {
  render(<ApiKeyDialog />);
  askForKey();
  expect(screen.getByText('API key needed')).toBeInTheDocument();
  expect(screen.getByText(/asks for an API key/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
});

test('stores the typed key for this tab and reloads', () => {
  render(<ApiKeyDialog />);
  askForKey();

  fireEvent.change(screen.getByLabelText('API key'), { target: { value: '  my-key  ' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }));

  expect(getApiKey()).toBe('my-key');
  expect(window.location.reload).toHaveBeenCalledTimes(1);
});

test('the key field hides what is typed', () => {
  render(<ApiKeyDialog />);
  askForKey();
  expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password');
});

test('says so when a stored key is refused, and forgets that key', () => {
  setApiKey('old-key');
  render(<ApiKeyDialog />);

  askForKey();

  expect(screen.getByText(/did not accept that key/)).toBeInTheDocument();
  expect(getApiKey()).toBe('');
});

test('stops listening when it is removed', () => {
  const { unmount } = render(<ApiKeyDialog />);
  unmount();
  expect(() => askForKey()).not.toThrow();
});
