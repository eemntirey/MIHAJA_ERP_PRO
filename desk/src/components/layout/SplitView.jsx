// src/components/layout/SplitView.jsx
import React from 'react';
import ResizablePanel from './ResizablePanel';
import './SplitView.css';

// Vue séparée côte à côte : liste/filtres à gauche, détail/édition à droite.
// La largeur du panneau gauche est contrôlée et persistée par le parent (par module).
const SplitView = ({
  left,
  right,
  module,
  leftWidth = 40,
  onResizeWidth,
  minWidth = 320,
  maxWidth = 60,
}) => {
  return (
    <div className="split-view" data-module={module}>
      <ResizablePanel
        className="split-view__left"
        width={leftWidth}
        onResize={onResizeWidth}
        minWidth={minWidth}
        maxWidth={maxWidth}
      >
        {left}
      </ResizablePanel>
      <div className="split-view__right" role="complementary" aria-label="Panneau de détail">
        {right}
      </div>
    </div>
  );
};

export default SplitView;
