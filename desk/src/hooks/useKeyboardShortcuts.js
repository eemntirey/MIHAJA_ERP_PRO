// src/hooks/useKeyboardShortcuts.js
// Hook de raccourcis clavier globaux pour l'application desktop.
import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDesktop } from '../contexts/DesktopContext';

/**
 * Active les raccourcis clavier globaux du bureau :
 * - CMD+K / CTRL+K : Ouvrir la palette de commandes
 * - CMD+B / CTRL+B : Basculer la barre laterale
 * - CMD+N / CTRL+N : Nouvelle entree (selon le contexte)
 * - CMD+F / CTRL+F : Focuser la recherche (palette)
 *
 * @param {{ onToggleSidebar?: () => void, onNew?: () => void }} options
 */
export const useKeyboardShortcuts = ({ onToggleSidebar, onNew } = {}) => {
  const { setCommandPaletteOpen } = useDesktop();
  const navigate = useNavigate();

  const handleKeyDown = useCallback((event) => {
    const mod = event.metaKey || event.ctrlKey;
    if (!mod) return;

    const key = event.key.toLowerCase();

    // CMD+K ou CMD+F : ouvrir la palette de commandes / recherche
    if (key === 'k' || key === 'f') {
      event.preventDefault();
      setCommandPaletteOpen(true);
      return;
    }

    // CMD+B : basculer la barre laterale
    if (key === 'b') {
      event.preventDefault();
      if (onToggleSidebar) onToggleSidebar();
      return;
    }

    // CMD+N : nouvelle entree (si callback fourni)
    if (key === 'n') {
      event.preventDefault();
      if (onNew) onNew();
      return;
    }

    // CMD+1..9 : navigation rapide vers les modules
    const moduleShortcuts = {
      '1': '/dashboard',
      '2': '/products',
      '3': '/clients',
      '4': '/sales',
      '5': '/invoices',
      '6': '/inventory',
      '7': '/suppliers',
      '8': '/hr',
      '9': '/accounting',
    };

    if (moduleShortcuts[event.key]) {
      event.preventDefault();
      navigate(moduleShortcuts[event.key]);
    }
  }, [setCommandPaletteOpen, onToggleSidebar, onNew, navigate]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

export default useKeyboardShortcuts;
