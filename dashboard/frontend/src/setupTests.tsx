import '@testing-library/jest-dom/vitest'; // for Vitest, not just jest-dom!
import { vi } from 'vitest';

vi.mock("./components/ui/form", async () => {
  const actual = await vi.importActual("./components/ui/form");
  return {
    ...actual,
    Form: ({ children }) => <div data-testid="form-mock">{children}</div>,
    FormDescription: ({ children }) => <div>{children}</div>,
  };
});