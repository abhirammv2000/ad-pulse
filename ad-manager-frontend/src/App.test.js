import { render, screen } from '@testing-library/react';
import axios from 'axios';
import App from './App';

// HomePage fires ad-server requests on mount (see AdPopUp in HomePage.js);
// this test is only checking that the app frame renders, so axios is mocked
// to avoid a real network call and the console noise from it failing.
jest.mock('axios');

beforeEach(() => {
  axios.post.mockResolvedValue({ data: {} });
  axios.get.mockResolvedValue({ data: {} });
});

test('renders the Ad Pulse homepage', () => {
  render(<App />);
  expect(screen.getByText('Welcome to Ad Pulse')).toBeInTheDocument();
});
