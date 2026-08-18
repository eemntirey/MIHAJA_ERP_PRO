// src/hooks/useKeyboardShortcuts.js
import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDesktop } from '../contexts/DesktopContext';

export const useKeyboardShortcuts = () => {
  const navigate = useNavigate();
  const { setCommandPaletteOpen, toggleSidebar } = useDesktop();

  const handleKeyDown = useCallback((e) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modKey = isMac ? e.metaKey : e.ctrlKey;

    if (modKey && e.key === 'k') {
      e.preventDefault();
      setCommandPaletteOpen((prev) => !prev);
    }
    if (modKey && e.key === 'n') {
      e.preventDefault();
      const path = window.location.pathname;
      if (path.includes('products')) navigate('/products');
      else if (path.includes('clients')) navigate('/clients');
      else if (path.includes('sales')) navigate('/sales');
      else if (path.includes('invoices')) navigate('/invoices');
      else navigate('/dashboard');
    }
    if (modKey && e.key === 'b') {
      e.preventDefault();
      toggleSidebar();
    }
    if (modKey && e.key === 'f') {
      e.preventDefault();
      const searchInput = document.querySelector('.global-search-input');
      if (searchInput) searchInput.focus();
    }
    if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  }, [navigate, setCommandPaletteOpen, toggleSidebar]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};
