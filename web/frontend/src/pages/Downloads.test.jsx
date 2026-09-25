import React from 'react';
import { render, screen } from '@testing-library/react';
import Downloads from './Downloads';

jest.mock('react-router-dom', () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

jest.mock('./Pages.css', () => ({}));

describe('Downloads', () => {
  it('propose un téléchargement Desktop direct et masque les apps non publiées', () => {
    render(<Downloads />);

    expect(screen.getByRole('link', { name: /Télécharger ERP Pro Desktop/i }).getAttribute('href'))
      .toBe('https://github.com/eemntirey/MIHAJA_ERP_PRO/releases/download/desktop-latest/MIHAJA-ERP-PRO-Setup.exe');

    expect(screen.getByText(/Bientôt disponible/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Télécharger ERP Pro Mobile/i })).not.toBeInTheDocument();
  });
});
