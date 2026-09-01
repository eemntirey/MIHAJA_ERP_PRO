import React from 'react';
import ErrorBoundary from '../ErrorBoundary';

describe('ErrorBoundary', () => {
  let origConsoleError;
  beforeEach(() => {
    origConsoleError = console.error;
    console.error = () => {};
  });
  afterEach(() => {
    console.error = origConsoleError;
  });

  it('classe exportée existe et hérite de Component', () => {
    expect(typeof ErrorBoundary).toBe('function');
    const proto = ErrorBoundary.prototype;
    expect(typeof proto.componentDidCatch).toBe('function');
    expect(typeof proto.render).toBe('function');
    expect(typeof ErrorBoundary.getDerivedStateFromError).toBe('function');
  });

  it('getDerivedStateFromError bascule hasError=true', () => {
    const sentinel = new Error('sentinel');
    const state = ErrorBoundary.getDerivedStateFromError(sentinel);
    expect(state.hasError).toBe(true);
    expect(state.error).toBe(sentinel);
  });

  it('componentDidCatch enregistre errorInfo dans le state', () => {
    const inst = new ErrorBoundary({ children: null });
    inst.state = { hasError: true, error: new Error('prev'), errorInfo: null };
    inst.setState = (partial) => { inst.state = { ...inst.state, ...partial }; };
    const info = { componentStack: 'stack' };
    inst.componentDidCatch(new Error('sentinel'), info);
    expect(inst.state.errorInfo).toBe(info);
  });

  it('render renvoie les children en fonctionnement normal', () => {
    const inst = new ErrorBoundary({ children: 'X' });
    inst.state = { hasError: false, error: null, errorInfo: null };
    expect(inst.render()).toBe('X');
  });

  it('render renvoie le fallback en cas d\'erreur', () => {
    const inst = new ErrorBoundary({ fallbackTitle: 'Titre X' });
    inst.state = { hasError: true, error: new Error('boom'), errorInfo: null };
    const tree = inst.render();
    expect(React.isValidElement(tree)).toBe(true);
    expect(tree.props.role).toBe('alert');
  });
});