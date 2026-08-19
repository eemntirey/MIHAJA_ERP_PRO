// src/test-helpers/renderDom.js
// Aides de test légères (react-dom + act) : le projet Desktop n'embarque pas
// @testing-library, ces utilitaires suffisent pour piloter le DOM dans jsdom.

import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';

/**
 * Prépare jsdom pour @tanstack/react-virtual :
 *  - `getRect` lit offsetWidth/offsetHeight (0 par défaut dans jsdom)
 *  - ResizeObserver n'existe pas dans jsdom
 */
export const setupVirtualEnvironment = ({ viewportHeight = 600, viewportWidth = 1000 } = {}) => {
  global.IS_REACT_ACT_ENVIRONMENT = true;

  if (!global.ResizeObserver) {
    global.ResizeObserver = class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }

  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    get() {
      return this.classList && this.classList.contains('dt-viewport') ? viewportHeight : 0;
    },
  });

  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    get() {
      return viewportWidth;
    },
  });
};

export const mountComponent = (element) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  let root;
  act(() => {
    root = createRoot(container);
    root.render(element);
  });
  return {
    container,
    rerender: (next) => act(() => root.render(next)),
    unmount: () => {
      act(() => root.unmount());
      container.remove();
    },
  };
};

export const clickNode = (node, init = {}) =>
  act(() => {
    node.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ...init }));
  });

export const dispatchMouse = (target, type, init = {}) =>
  act(() => {
    target.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, ...init }));
  });

// Définit la valeur via le setter natif pour contourner le « value tracker »
// de React (sinon React ignore la mutation directe de `.value`).
const setNativeValue = (node, value) => {
  const proto =
    node.tagName === 'SELECT'
      ? window.HTMLSelectElement.prototype
      : node.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
  descriptor.set.call(node, value);
};

export const changeInput = (node, value) =>
  act(() => {
    setNativeValue(node, value);
    node.dispatchEvent(new Event('input', { bubbles: true }));
    node.dispatchEvent(new Event('change', { bubbles: true }));
  });

export const submitForm = (form) =>
  act(() => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });

/** Laisse passer un tick + une frame d'animation (throttle rAF du resize). */
export const flushFrames = async () => {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 40));
  });
};

export const textOf = (node) => (node ? node.textContent.trim() : '');

export const rowTexts = (container, columnIndex) =>
  Array.from(container.querySelectorAll('tbody tr.dt-row')).map((row) =>
    textOf(row.querySelectorAll('td')[columnIndex])
  );

export { act };
