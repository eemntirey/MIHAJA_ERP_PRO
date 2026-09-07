import React from 'react';
import './ui.css';

export const Skeleton = ({ circle = false, width, height, className = '', style = {} }) => (
  <span
    className={`skeleton ${circle ? 'skeleton--circle' : ''} ${className}`}
    style={{ width, height, ...style }}
    aria-hidden="true"
  />
);

export const SkeletonText = ({ lines = 3 }) => (
  <div aria-hidden="true">
    <span className="skeleton skeleton--title" />
    {Array.from({ length: lines }).map((_, i) => (
      <span key={i} className="skeleton skeleton--text" style={{ width: `${90 - i * 12}%` }} />
    ))}
  </div>
);

export const SkeletonTable = ({ rows = 6, cols = 5 }) => (
  <div aria-hidden="true">
    {Array.from({ length: rows }).map((_, r) => (
      <div key={r} style={{ display: 'flex', gap: 12, padding: '12px 0' }}>
        {Array.from({ length: cols }).map((_, c) => (
          <Skeleton key={c} height={14} width={`${100 / cols}%`} />
        ))}
      </div>
    ))}
  </div>
);
