// src/components/layout/SplitView.jsx
import React from 'react';
import ResizablePanel from './ResizablePanel';
import './SplitView.css';

const SplitView = ({ left, right, module }) => {
  return (
    <div className="split-view" data-module={module}>
      <ResizablePanel
        className="split-view__left"
        initialWidth={40}
        minWidth={320}
        maxWidth={60}
      >
        {left}
      </ResizablePanel>
      <div className="split-view__divider" aria-hidden="true" />
      <div className="split-view__right">
        {right}
      </div>
    </div>
  );
};

export default SplitView;
