import React from 'react';
import ErrorBoundary from './ErrorBoundary';

describe('ErrorBoundary component export (super-admin)', () => {
  test('exporte un composant React valide', () => {
    expect(typeof ErrorBoundary).toBe('function');
  });

  test('definit getDerivedStateFromError statique', () => {
    expect(typeof ErrorBoundary.getDerivedStateFromError).toBe('function');
    const state = ErrorBoundary.getDerivedStateFromError(new Error('test'));
    expect(state).toEqual({ hasError: true, error: expect.any(Error) });
  });

  test('initial state a hasError=false', () => {
    const instance = new ErrorBoundary({ children: null });
    expect(instance.state).toEqual({ hasError: false, error: null });
  });
});