// src/contexts/DesktopContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

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
  const [notifications, setNotifications] = useState([
    { id: 1, title: 'Nouvelle commande', message: 'Commande #1042 reçue', time: '2 min', read: false },
    { id: 2, title: 'Stock critique', message: 'Produit XYZ sous le seuil', time: '15 min', read: false },
    { id: 3, title: 'Paiement reçu', message: 'Facture #89 payée', time: '1h', read: true },
  ]);

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
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n));
  }, []);
  const setNotificationsList = useCallback((next) => {
    setNotifications(Array.isArray(next) ? next : []);
  }, []);
  const addNotification = useCallback((notification) => {
    setNotifications((prev) => {
      const exists = prev.some((n) => n.id === notification.id);
      return exists ? prev : [notification, ...prev];
    });
  }, []);
  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
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

