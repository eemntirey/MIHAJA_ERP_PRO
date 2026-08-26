// src/contexts/DesktopContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { notificationService } from '../services/desktopApi';
import { NOTIFICATION_EVENTS } from '../utils/notify';

const DesktopContext = createContext();

const LS_KEYS = {
  sidebarCollapsed: 'desk_sidebar_collapsed',
  splitView: 'desk_split_view',
  commandPaletteOpen: 'desk_command_palette_open',
};

export const useDesktop = () => {
  const context = useContext(DesktopContext);
  if (!context) throw new Error('useDesktop must be used within a DesktopProvider');
  return context;
};

export const DesktopProvider = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_KEYS.sidebarCollapsed) === 'true'; }
    catch { return false; }
  });
  const [splitView, setSplitView] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS_KEYS.splitView) || '{}'); }
    catch { return {}; }
  });
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [notifications, setNotificationsState] = useState(() => {
    try {
      return notificationService.readAll();
    } catch {
      return [];
    }
  });

  // Persistance notifications en localStorage + synchronisation du badge Electron
  useEffect(() => {
    notificationService.save(notifications).catch(() => {});
    const unread = notifications.filter((n) => !n.read).length;
    notificationService.setBadge(unread).catch(() => {});
  }, [notifications]);

  // Réagir aux notifications ajoutées depuis l'extérieur (utilitaire notify.js)
  useEffect(() => {
    const handler = () => setNotificationsState(notificationService.readAll());
    window.addEventListener(NOTIFICATION_EVENTS.UPDATED, handler);
    return () => window.removeEventListener(NOTIFICATION_EVENTS.UPDATED, handler);
  }, []);

  useEffect(() => {
    try { localStorage.setItem(LS_KEYS.sidebarCollapsed, String(sidebarCollapsed)); }
    catch {}
  }, [sidebarCollapsed]);

  useEffect(() => {
    try { localStorage.setItem(LS_KEYS.splitView, JSON.stringify(splitView)); }
    catch {}
  }, [splitView]);

  const toggleSplitView = useCallback((module) => {
    setSplitView((prev) => {
      const cur = prev[module] || { enabled: false, leftWidth: 40 };
      return { ...prev, [module]: { ...cur, enabled: !cur.enabled } };
    });
  }, []);

  const setSplitWidth = useCallback((module, width) => {
    setSplitView((prev) => {
      const cur = prev[module] || { enabled: false, leftWidth: 40 };
      return { ...prev, [module]: { ...cur, leftWidth: width } };
    });
  }, []);

  const toggleSidebar = useCallback(() => setSidebarCollapsed((prev) => !prev), []);
  const markNotificationRead = useCallback((id) => {
    setNotificationsState((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n));
  }, []);
  const setNotificationsList = useCallback((next) => {
    setNotificationsState((prev) => {
      if (typeof next === 'function') {
        const result = next(prev);
        return Array.isArray(result) ? result : [];
      }
      return Array.isArray(next) ? next : prev;
    });
  }, []);
  const addNotification = useCallback((notification) => {
    const id = notification.id || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    const formatted = {
      id,
      title: notification.title || 'Notification',
      message: notification.message || '',
      time: notification.time || '',
      read: false,
    };
    setNotificationsState((prev) => {
      const exists = prev.some((n) => n.id === id);
      if (exists) return prev;
      return [formatted, ...prev];
    });
    notificationService.triggerNative(formatted.title, formatted.message).catch(() => {});
  }, []);
  const removeNotification = useCallback((id) => {
    setNotificationsState((prev) => prev.filter((n) => n.id !== id));
  }, []);
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <DesktopContext.Provider value={{
      sidebarCollapsed, toggleSidebar, splitView, setSplitView, toggleSplitView, setSplitWidth, commandPaletteOpen, setCommandPaletteOpen,
      notifications, markNotificationRead, setNotificationsList, addNotification, removeNotification, unreadCount,
    }}>
      {children}
    </DesktopContext.Provider>
  );
};

