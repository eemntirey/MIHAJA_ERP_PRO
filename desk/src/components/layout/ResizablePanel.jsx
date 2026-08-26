// src/components/layout/ResizablePanel.jsx
import React, { useState, useRef, useCallback, useEffect } from 'react';
import './ResizablePanel.css';

// Panneau redimensionnable (glisser la poignée verticale).
// Composant contrôlé : `width` (en %) + `onResize(width)` permettent de persister
// la largeur (ex: par module via localStorage). Sinon largeur interne.
const ResizablePanel = ({
  children,
  className,
  width,
  onResize,
  minWidth = 320,
  maxWidth = 60,
}) => {
  const isControlled = typeof width === 'number';
  const panelRef = useRef(null);
  const [internalWidth, setInternalWidth] = useState(() => {
    const parent = panelRef.current?.parentElement;
    const rect = parent?.getBoundingClientRect();
    if (rect?.width && rect.width >= minWidth) {
      return Math.min(maxWidth, (minWidth / rect.width) * 100);
    }
    return 40;
  });
  const current = isControlled ? width : internalWidth;
  const [isResizing, setIsResizing] = useState(false);

  const startResize = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const onMove = (e) => {
      const parent = panelRef.current?.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      if (!rect.width) return;
      const px = e.clientX - rect.left;
      const minPct = (minWidth / rect.width) * 100;
      const pct = Math.max(minPct, Math.min(maxWidth, (px / rect.width) * 100));
      if (isControlled) onResize?.(pct);
      else setInternalWidth(pct);
    };

    const onUp = () => setIsResizing(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, minWidth, maxWidth, isControlled, onResize]);

  return (
    <div
      ref={panelRef}
      className={`resizable-panel ${className || ''} ${isResizing ? 'resizing' : ''}`}
      style={{ width: `${current}%`, minWidth: `${minWidth}px`, maxWidth: `${maxWidth}%` }}
    >
      {children}
      <div
        className="resizable-panel__handle"
        onMouseDown={startResize}
        role="separator"
        aria-orientation="vertical"
        aria-label="Redimensionner le panneau"
      />
    </div>
  );
};

export default ResizablePanel;
