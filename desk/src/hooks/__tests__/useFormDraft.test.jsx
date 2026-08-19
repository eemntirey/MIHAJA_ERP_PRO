// src/hooks/__tests__/useFormDraft.test.jsx
import React, { useState } from 'react';
import useFormDraft from '../useFormDraft';
import { draftService } from '../../services/draftService';
import { setupVirtualEnvironment, mountComponent, act } from '../../test-helpers/renderDom';

setupVirtualEnvironment();

let captured = {};
const Harness = ({ dkey, initial, interval = 2000, exclude }) => {
  const [values, setValues] = useState(initial);
  const draft = useFormDraft(dkey, values, { enabled: true, interval, exclude });
  captured.draft = draft;
  captured.setValues = setValues;
  return <div data-testid="status">{draft.status}</div>;
};

beforeEach(() => {
  localStorage.clear();
  captured = {};
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('useFormDraft', () => {
  test('auto-save après modification et délai', () => {
    mountComponent(<Harness dkey="draft:1" initial={{ name: 'a' }} interval={2000} />);
    act(() => captured.setValues({ name: 'b' }));
    act(() => jest.advanceTimersByTime(2000));
    expect(draftService.get('draft:1').data).toEqual({ name: 'b' });
  });

  test("n'écrit rien tant que le formulaire n'a pas changé", () => {
    mountComponent(<Harness dkey="draft:2" initial={{ name: 'a' }} interval={2000} />);
    act(() => jest.advanceTimersByTime(2000));
    expect(draftService.get('draft:2')).toBeNull();
    expect(captured.draft.saveNow()).toBe(false);
  });

  test('saveNow force l’écriture', () => {
    mountComponent(<Harness dkey="draft:3" initial={{ name: 'a' }} interval={100000} />);
    expect(captured.draft.saveNow(true)).toBe(true);
    expect(draftService.get('draft:3').data).toEqual({ name: 'a' });
  });

  test('restore renvoie le brouillon existant', () => {
    draftService.save('draft:4', { x: 1 });
    mountComponent(<Harness dkey="draft:4" initial={{ x: 0 }} interval={100000} />);
    let restored;
    act(() => {
      restored = captured.draft.restore();
    });
    expect(restored).toEqual({ x: 1 });
    expect(captured.draft.hasStoredDraft).toBe(false);
  });

  test('discard supprime le brouillon', () => {
    draftService.save('draft:5', { x: 1 });
    mountComponent(<Harness dkey="draft:5" initial={{ x: 0 }} interval={100000} />);
    act(() => captured.draft.discard());
    expect(draftService.get('draft:5')).toBeNull();
  });

  test('flush au démontage persiste la dernière saisie', () => {
    const { unmount } = mountComponent(<Harness dkey="draft:6" initial={{ name: 'a' }} interval={100000} />);
    act(() => captured.setValues({ name: 'z' }));
    unmount();
    expect(draftService.get('draft:6').data).toEqual({ name: 'z' });
  });

  test('exclut les champs marqués (exclude)', () => {
    mountComponent(<Harness dkey="draft:7" initial={{ name: 'a', token: 'secret' }} interval={1000} exclude={['token']} />);
    act(() => captured.setValues({ name: 'b', token: 'secret' }));
    act(() => jest.advanceTimersByTime(1000));
    expect(draftService.get('draft:7').data).toEqual({ name: 'b' });
    expect(draftService.get('draft:7').data.token).toBeUndefined();
  });
});
