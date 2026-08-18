import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { NAV_ITEMS } from './navConfig';
import './CommandPalette.css';

const QUICK_ACTIONS = [
  { id: 'qa-sale', label: 'Nouvelle vente', icon: 'ti-shopping-cart', to: '/sales', kind: 'action' },
  { id: 'qa-client', label: 'Nouveau client', icon: 'ti-user-plus', to: '/clients', kind: 'action' },
  { id: 'qa-product', label: 'Nouveau produit', icon: 'ti-package', to: '/products', kind: 'action' },
  { id: 'qa-ca', label: 'Exporter le chiffre d’affaires', icon: 'ti-download', to: '/accounting', kind: 'action' },
];

// Score flou simple : correspondance de sous-séquence.
const fuzzyScore = (query, text) => {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (t.includes(q)) return 3;
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i += 1) {
    if (t[i] === q[qi]) qi += 1;
  }
  return qi === q.length ? 1 : 0;
};

const CommandPalette = ({ open, onClose }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActive(0);
      const id = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [open]);

  const items = useMemo(() => {
    const all = [
      ...QUICK_ACTIONS,
      ...NAV_ITEMS.map((n) => ({ ...n, kind: 'page' })),
    ];
    if (!query) {
      return [
        ...QUICK_ACTIONS,
        ...NAV_ITEMS.map((n) => ({ ...n, kind: 'page' })),
      ];
    }
    return all
      .map((item) => ({ ...item, _score: fuzzyScore(query, item.label) }))
      .filter((item) => item._score > 0)
      .sort((a, b) => b._score - a._score);
  }, [query]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  if (!open) return null;

  const go = (item) => {
    if (item && item.to) {
      navigate(item.to);
      onClose();
    }
  };

  const onKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      go(items[active]);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
    }
  };

  return (
    <div className="command-overlay" onMouseDown={onClose}>
      <div
        className="command-palette"
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Palette de commandes"
      >
        <div className="command-palette__input">
          <i className="ti ti-search" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Rechercher pages, actions, clients, produits…"
            aria-label="Recherche"
          />
          <kbd>ESC</kbd>
        </div>

        <ul className="command-palette__list">
          {items.length === 0 && (
            <li className="command-palette__empty">Aucun résultat</li>
          )}
          {items.map((item, idx) => (
            <li
              key={item.id || item.path}
              className={`command-palette__item${idx === active ? ' is-active' : ''}`}
              onMouseEnter={() => setActive(idx)}
              onMouseDown={() => go(item)}
            >
              <i className={`ti ${item.icon}`} aria-hidden="true" />
              <span className="command-palette__label">{item.label}</span>
              <span className="command-palette__hint">
                {item.kind === 'action' ? 'Action' : 'Page'}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default CommandPalette;
