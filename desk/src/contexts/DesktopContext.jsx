// src/contexts/DesktopContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const DesktopContext = createContext();

const LS_KEYS = {
  sidebarCollapsed: 'desk_sidebar_collapsed',
  favorites: 'desk_favorites',
  splitView: 'desk_split_view',
  tableColumns: 'desk_table_columns',
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
  const [favorites, setFavorites] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS_KEYS.favorites) || '[]'); }
    catch { return []; }
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
    try { localStorage.setItem(LS_KEYS.favorites, JSON.stringify(favorites.slice(0, 6))); }
    catch {}
  }, [favorites]);

  useEffect(() => {
    try { localStorage.setItem(LS_KEYS.splitView, JSON.stringify(splitView)); }
    catch {}
  }, [splitView]);

  const toggleSidebar = useCallback(() => setSidebarCollapsed((prev) => !prev), []);
  const toggleFavorite = useCallback((item) => {
    setFavorites((prev) => {
      const exists = prev.find((f) => f.to === item.to);
      if (exists) return prev.filter((f) => f.to !== item.to);
      return [...prev, item].slice(0, 6);
    });
  }, []);
  const isFavorite = useCallback((to) => favorites.some((f) => f.to === to), [favorites]);
  const markNotificationRead = useCallback((id) => {
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n));
  }, []);
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <DesktopContext.Provider value={{
      sidebarCollapsed, toggleSidebar, favorites, toggleFavorite, isFavorite,
      splitView, setSplitView, commandPaletteOpen, setCommandPaletteOpen,
      notifications, markNotificationRead, unreadCount,
    }}>
      {children}
    </DesktopContext.Provider>
  );
};
