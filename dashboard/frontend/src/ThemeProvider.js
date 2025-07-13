import React from 'react';
import { ThemeProvider as NextThemeProvider } from 'next-themes';

export default function ThemeProvider({ children }) {
  return (
    <NextThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </NextThemeProvider>
  );
}
