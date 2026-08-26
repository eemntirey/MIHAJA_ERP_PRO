// src/contexts/__tests__/DesktopContext.notifications.test.jsx
import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { DesktopProvider, useDesktop } from '../DesktopContext';
import { notificationService } from '../../services/desktopApi';
import { NOTIFICATION_EVENTS } from '../../utils/notify';

const buildKey = (area, name, scoped = true) =>
  scoped ? `erp.desk.${area}.${name}` : `erp.desk.${area}.${name}`;

const STORAGE_KEY = buildKey('notifications', 'list', false);

const Harness = () => {
  const {
    notifications, unreadCount, addNotification, markNotificationRead,
    removeNotification, setNotificationsList,
  } = useDesktop();

  // Sync external events back to the harness for assertions
  useEffect(() => {
    const handler = () => {
      const list = notificationService.readAll();
      setNotificationsList(list);
    };
    window.addEventListener(NOTIFICATION_EVENTS.UPDATED, handler);
    return () => window.removeEventListener(NOTIFICATION_EVENTS.UPDATED, handler);
  }, [setNotificationsList]);

  window.__harness = {
    notifications, unreadCount, addNotification, markNotificationRead,
    removeNotification, setNotificationsList,
  };

  return (
    <div>
      <span data-testid="unread-count">{unreadCount}</span>
      <span data-testid="notif-list">{notifications.length}</span>
    </div>
  );
};

describe('DesktopContext — notifications', () => {
  let container, root;

  beforeEach(() => {
    localStorage.clear();
    window.__harness = null;
  });

  afterEach(() => {
    if (root) {
      act(() => root.unmount());
    }
    container?.remove();
    window.__harness = null;
  });

  test('charge les notifications depuis le localStorage', async () => {
    const stored = [
      { id: 'a', title: 'Persisted', message: 'msg', time: 'now', read: false },
    ];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));

    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    expect(window.__harness.notifications).toHaveLength(1);
    expect(window.__harness.notifications[0].title).toBe('Persisted');
  });

  test('utilise les notifications par défaut quand le localStorage est vide', () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    expect(window.__harness.notifications.length).toBe(3);
  });

  test('addNotification incrémente la liste et le badge', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    const initialCount = window.__harness.notifications.length;

    await act(async () => {
      window.__harness.addNotification({ title: 'New', message: 'Hello' });
    });

    expect(window.__harness.notifications.length).toBe(initialCount + 1);
    expect(window.__harness.unreadCount).toBe(3);
  });

  test('addNotification persiste en localStorage', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    await act(async () => {
      window.__harness.addNotification({ title: 'Persisted Notif', message: 'm' });
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    expect(stored.find((n) => n.title === 'Persisted Notif')).toBeDefined();
  });

  test('addNotification ne duplique pas une notification existante', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    await act(async () => {
      window.__harness.addNotification({ id: 'existing', title: 'Dup', message: 'm' });
    });
    await act(async () => {
      window.__harness.addNotification({ id: 'existing', title: 'Dup 2', message: 'm2' });
    });

    const existingCount = window.__harness.notifications.filter((n) => n.id === 'existing');
    expect(existingCount).toHaveLength(1);
  });

  test('markNotificationRead décrémente le badge', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    const unread = window.__harness.notifications.find((n) => !n.read);
    expect(unread).toBeDefined();

    await act(async () => {
      window.__harness.markNotificationRead(unread.id);
    });

    expect(window.__harness.unreadCount).toBe(1);
  });

  test('removeNotification supprime la notification', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    const initialLength = window.__harness.notifications.length;
    const toRemove = window.__harness.notifications[0];

    await act(async () => {
      window.__harness.removeNotification(toRemove.id);
    });

    expect(window.__harness.notifications.length).toBe(initialLength - 1);
  });

  test('setNotificationsList remplace la liste', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    const newList = [{ id: 'new-1', title: 'Custom', message: 'm', time: 'now', read: false }];

    await act(async () => {
      window.__harness.setNotificationsList(newList);
    });

    expect(window.__harness.notifications).toEqual(newList);
  });

  test('événement notifications:updated synchronise le contexte', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => {
      root.render(<DesktopProvider><Harness /></DesktopProvider>);
    });

    const before = window.__harness.notifications.length;

    // Simulate external add via localStorage
    notificationService.add({ title: 'External', message: 'from outside' });

    await act(async () => {
      window.dispatchEvent(new CustomEvent(NOTIFICATION_EVENTS.UPDATED));
    });

    expect(window.__harness.notifications.length).toBe(before + 1);
    expect(window.__harness.notifications.find((n) => n.title === 'External')).toBeDefined();
  });
});
