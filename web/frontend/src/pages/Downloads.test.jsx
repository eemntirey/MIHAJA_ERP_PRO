import React from 'react';
import { render, screen } from '@testing-library/react';
import Downloads from './Downloads';

jest.mock('react-router-dom', () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

jest.mock('./Pages.css', () => ({}));

describe('Downloads', () => {
  it('propose les téléchargements Desktop et Mobile', () => {
    render(<Downloads />);

    expect(screen.getByRole('link', { name: /Télécharger ERP Pro Desktop/i }).getAttribute('href'))
      .toBe('https://github.com/eemntirey/MIHAJA_ERP_PRO/releases/latest/download/ERP-Pro-Desktop-Setup.exe');
    expect(screen.getByRole('link', { name: /Télécharger ERP Pro Mobile/i }).getAttribute('href'))
      .toBe('https://github.com/eemntirey/MIHAJA_ERP_PRO/releases/latest/download/ERP-Pro-Mobile.apk');
  });
});
