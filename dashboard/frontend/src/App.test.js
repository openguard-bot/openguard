import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('renders without crashing', () => {
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <App />
    </MemoryRouter>
  );
});

test('renders OpenGuard Dashboard text', () => {
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <App />
    </MemoryRouter>
  );
  const linkElement = screen.getByText(/OpenGuard Dashboard/i);
  expect(linkElement).toBeInTheDocument();
});
