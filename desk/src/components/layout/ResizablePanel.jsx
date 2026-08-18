// src/components/layout/ResizablePanel.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import './ResizablePanel.css';

const ResizablePanel = ({ children, className, initialWidth = 40, minWidth = 20, maxWidth = 60 }) => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef(null);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      if (!panelRef.current) return;
      const parent = panelRef.current.parentElement;
      if (!parent) return;
      const parentWidth = parent.getBoundingClientRect().width;
      const newWidth = (e.clientX / parentWidth) * 100;
      setWidth(Math.max(minWidth, Math.min(maxWidth, newWidth)));
    };
    const handleMouseUp = () => setIsResizing(false);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, minWidth, maxWidth]);

  return (
    <div
      ref={panelRef}
      className={`resizable-panel ${className || ''} ${isResizing ? 'resizing' : ''}`}
      style={{ width: `${width}%` }}
    >
      {children}
      <div className="resizable-panel__handle" onMouseDown={handleMouseDown} />
    </div>
  );
};

export default ResizablePanel;
