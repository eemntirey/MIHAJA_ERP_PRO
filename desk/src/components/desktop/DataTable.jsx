// src/components/desktop/DataTable.jsx
//
// DataTable Desktop — grille de données haute volumétrie.
//
//  • Tri multi-critères        : clic = tri simple (asc → desc → aucun), Shift+clic = ajout d'un critère
//  • Redimensionnement         : drag & drop sur le séparateur d'entête (+ flèches clavier, double-clic = reset)
//  • Sélection multiple        : cases à cocher, Shift+clic = plage, barre d'actions groupées
//  • Virtualisation            : @tanstack/react-virtual (activée automatiquement au-delà du seuil)
//  • Persistance               : largeurs / colonnes masquées par module (columnConfigService → localStorage)
//
// Exemple :
//   <DataTable
//     module="produits"
//     columns={columns}
//     data={rows}
//     selectable
//     bulkActions={[{ key: 'delete', label: 'Supprimer', variant: 'danger', onClick: (ids) => ... }]}
//   />

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { columnConfigService } from '../../services/desktopApi';
import './DataTable.css';

export const DEFAULT_COLUMN_WIDTH = 160;
export const MIN_COLUMN_WIDTH = 64;
export const MAX_COLUMN_WIDTH = 900;
export const SELECTION_COLUMN_WIDTH = 44;
export const VIRTUALIZATION_THRESHOLD = 80;
const RESIZE_KEYBOARD_STEP = 16;
const CONFIG_SAVE_DEBOUNCE = 400;

const collator = typeof Intl !== 'undefined' && Intl.Collator
  ? new Intl.Collator('fr', { numeric: true, sensitivity: 'base' })
  : { compare: (a, b) => (a === b ? 0 : a > b ? 1 : -1) };

const isNil = (value) => value === null || value === undefined || value === '';

const clampWidth = (value) => Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, Math.round(value)));

const toNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const parsed = Number(String(value).replace(/\s/g, '').replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
};

const toTime = (value) => {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.getTime();
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
};

/** Valeur affichée d'une cellule (supporte `accessor` et les clés imbriquées "a.b"). */
export const getCellValue = (row, column) => {
  if (!row || !column) return undefined;
  if (typeof column.accessor === 'function') return column.accessor(row);
  const { key } = column;
  if (!key) return undefined;
  if (key.indexOf('.') !== -1) {
    return key.split('.').reduce((acc, part) => (acc == null ? acc : acc[part]), row);
  }
  return row[key];
};

/** Valeur utilisée pour le tri (`sortAccessor` prioritaire sur la valeur affichée). */
export const getSortValue = (row, column) =>
  typeof column?.sortAccessor === 'function' ? column.sortAccessor(row) : getCellValue(row, column);

/** Comparateur typé (nombres, dates, booléens, texte FR avec tri naturel). */
export const compareValues = (a, b, type = 'auto') => {
  if (type === 'number') {
    const na = toNumber(a);
    const nb = toNumber(b);
    if (na !== null && nb !== null) return na - nb;
  }
  if (type === 'date') {
    const ta = toTime(a);
    const tb = toTime(b);
    if (ta !== null && tb !== null) return ta - tb;
  }
  if (typeof a === 'boolean' || typeof b === 'boolean') return (a ? 1 : 0) - (b ? 1 : 0);
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  if (a instanceof Date && b instanceof Date) return a.getTime() - b.getTime();
  return collator.compare(String(a), String(b));
};

/**
 * Tri multi-critères stable. Les valeurs vides sont toujours reléguées en fin de liste.
 * @param {Array} rows
 * @param {Array<{key:string,direction:'asc'|'desc'}>} sortState
 * @param {Map<string,Object>} columnMap
 */
export const sortRows = (rows, sortState, columnMap) => {
  const list = Array.isArray(rows) ? rows : [];
  if (!Array.isArray(sortState) || sortState.length === 0) return list;

  const criteria = sortState
    .map((entry) => ({
      direction: entry.direction === 'desc' ? 'desc' : 'asc',
      column: columnMap?.get(entry.key) || { key: entry.key },
    }))
    .filter((entry) => entry.column && entry.column.key);
  if (criteria.length === 0) return list;

  const decorated = list.map((row, index) => ({ row, index }));
  decorated.sort((left, right) => {
    for (let i = 0; i < criteria.length; i += 1) {
      const { column, direction } = criteria[i];
      const a = getSortValue(left.row, column);
      const b = getSortValue(right.row, column);
      const aNil = isNil(a);
      const bNil = isNil(b);
      if (aNil || bNil) {
        if (aNil && bNil) continue;
        return aNil ? 1 : -1; // vides toujours en bas, quel que soit le sens
      }
      const cmp = typeof column.sortComparator === 'function'
        ? column.sortComparator(a, b, left.row, right.row)
        : compareValues(a, b, column.sortType || column.type || 'auto');
      if (cmp !== 0) return direction === 'desc' ? -cmp : cmp;
    }
    return left.index - right.index; // tri stable
  });
  return decorated.map((entry) => entry.row);
};

/**
 * Calcule l'état de tri suivant.
 * - clic simple   : asc → desc → aucun (et remise à zéro des autres critères)
 * - Shift + clic  : ajoute le critère, puis asc → desc → retrait du critère
 */
export const nextSortState = (current, key, multi = false) => {
  const list = Array.isArray(current) ? current.map((entry) => ({ ...entry })) : [];
  const index = list.findIndex((entry) => entry.key === key);

  if (multi) {
    if (index === -1) {
      list.push({ key, direction: 'asc' });
      return list;
    }
    if (list[index].direction === 'asc') {
      list[index] = { key, direction: 'desc' };
      return list;
    }
    list.splice(index, 1);
    return list;
  }

  if (index === -1 || list.length > 1) return [{ key, direction: 'asc' }];
  return list[index].direction === 'asc' ? [{ key, direction: 'desc' }] : [];
};

const defaultCellContent = (value) => {
  if (isNil(value)) return '—';
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non';
  if (value instanceof Date) return value.toLocaleDateString('fr-FR');
  if (React.isValidElement(value)) return value;
  if (typeof value === 'object') return JSON.stringify(value);
  return value;
};

const DataTableRow = memo(function DataTableRow({
  row,
  rowId,
  index,
  columns,
  selectable,
  selected,
  onToggleRow,
  onRowClick,
  rowStyle,
  className,
}) {
  const handleClick = useCallback(
    (event) => {
      if (onRowClick) onRowClick(row, index, event);
    },
    [onRowClick, row, index]
  );

  const handleCheckbox = useCallback(
    (event) => {
      onToggleRow(rowId, index, event);
    },
    [onToggleRow, rowId, index]
  );

  const stopPropagation = useCallback((event) => event.stopPropagation(), []);

  return (
    <tr
      data-index={index}
      className={[
        'dt-row',
        selected ? 'is-selected' : '',
        onRowClick ? 'is-clickable' : '',
        className || '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={rowStyle}
      onClick={onRowClick ? handleClick : undefined}
      aria-selected={selectable ? selected : undefined}
    >
      {selectable && (
        <td className="dt-cell dt-cell--select" onClick={stopPropagation}>
          <input
            type="checkbox"
            checked={selected}
            onChange={handleCheckbox}
            onClick={stopPropagation}
            aria-label={`Sélectionner la ligne ${index + 1}`}
          />
        </td>
      )}
      {columns.map((column) => {
        const value = getCellValue(row, column);
        const content = column.render ? column.render(value, row, index) : defaultCellContent(value);
        const title = !column.render && (typeof value === 'string' || typeof value === 'number')
          ? String(value)
          : undefined;
        return (
          <td
            key={column.key}
            className={[
              'dt-cell',
              column.align ? `dt-align-${column.align}` : '',
              column.cellClassName || '',
            ]
              .filter(Boolean)
              .join(' ')}
            title={title}
          >
            {content}
          </td>
        );
      })}
      <td className="dt-cell dt-cell--filler" aria-hidden="true" />
    </tr>
  );
});

const DataTable = ({
  columns = [],
  data = [],
  rowKey = 'id',
  module,

  loading = false,
  emptyMessage = 'Aucune donnée',
  title,
  toolbar,
  showFooter = true,
  dense = false,
  className,

  onRowClick,
  rowClassName,

  // Tri
  multiSort = true,
  sort,
  onSortChange,
  defaultSort,

  // Colonnes
  resizable = true,
  columnToggle = true,
  defaultColumnWidth = DEFAULT_COLUMN_WIDTH,

  // Sélection
  selectable = false,
  selectedIds,
  onSelectionChange,
  bulkActions,

  // Virtualisation
  virtualized = 'auto',
  virtualizationThreshold = VIRTUALIZATION_THRESHOLD,
  rowHeight = 44,
  overscan = 8,
  height,
  maxHeight = 520,
}) => {
  const rows = Array.isArray(data) ? data : [];
  const safeColumns = useMemo(() => (Array.isArray(columns) ? columns.filter(Boolean) : []), [columns]);

  const viewportRef = useRef(null);
  const selectAllRef = useRef(null);
  const lastSelectedIndexRef = useRef(null);
  const resizeStateRef = useRef(null);
  const resizeFrameRef = useRef(null);
  const columnMenuRef = useRef(null);

  const [internalSort, setInternalSort] = useState(() => (Array.isArray(defaultSort) ? defaultSort : []));
  const [internalSelection, setInternalSelection] = useState([]);
  const [widths, setWidths] = useState({});
  const [hiddenKeys, setHiddenKeys] = useState([]);
  const [configLoaded, setConfigLoaded] = useState(!module);
  const [resizingKey, setResizingKey] = useState(null);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [busyBulkKey, setBusyBulkKey] = useState(null);

  /* ------------------------------------------------------------------ tri */

  const sortState = useMemo(() => {
    const source = Array.isArray(sort) ? sort : internalSort;
    return source.filter((entry) => entry && entry.key);
  }, [sort, internalSort]);

  const applySortState = useCallback(
    (next) => {
      if (!Array.isArray(sort)) setInternalSort(next);
      if (onSortChange) onSortChange(next);
      if (viewportRef.current) viewportRef.current.scrollTop = 0;
    },
    [onSortChange, sort]
  );

  const handleSortClick = useCallback(
    (columnKey, event) => {
      const useMulti = multiSort && !!(event?.shiftKey);
      applySortState(nextSortState(sortState, columnKey, useMulti));
    },
    [applySortState, multiSort, sortState]
  );

  /* -------------------------------------------------------------- colonnes */

  const visibleColumns = useMemo(
    () => safeColumns.filter((column) => column.visible !== false && !hiddenKeys.includes(column.key)),
    [safeColumns, hiddenKeys]
  );

  const columnMap = useMemo(() => {
    const map = new Map();
    safeColumns.forEach((column) => map.set(column.key, column));
    return map;
  }, [safeColumns]);

  const widthOf = useCallback(
    (column) => {
      const stored = widths[column.key];
      if (typeof stored === 'number' && Number.isFinite(stored)) return stored;
      if (typeof column.width === 'number') return column.width;
      return defaultColumnWidth;
    },
    [widths, defaultColumnWidth]
  );

  const totalWidth = useMemo(
    () => visibleColumns.reduce((sum, column) => sum + widthOf(column), selectable ? SELECTION_COLUMN_WIDTH : 0),
    [visibleColumns, widthOf, selectable]
  );

  // Chargement de la configuration persistée (largeurs + colonnes masquées).
  useEffect(() => {
    if (!module) {
      setConfigLoaded(true);
      return undefined;
    }
    let cancelled = false;
    setConfigLoaded(false);
    columnConfigService
      .get(module)
      .then((response) => {
        if (cancelled) return;
        const config = response?.data?.config || {};
        const loadedWidths = config.widths && typeof config.widths === 'object' ? config.widths : {};
        if (Object.keys(loadedWidths).length > 0) setWidths(loadedWidths);
        if (Array.isArray(config.hidden) && config.hidden.length > 0) setHiddenKeys(config.hidden);
      })
      .catch(() => {
        /* préférences non critiques */
      })
      .then(() => {
        if (!cancelled) setConfigLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [module]);

  // Sauvegarde (debounce) des préférences de colonnes.
  useEffect(() => {
    if (!module || !configLoaded) return undefined;
    const timer = setTimeout(() => {
      columnConfigService.save(module, { widths, hidden: hiddenKeys }).catch(() => {});
    }, CONFIG_SAVE_DEBOUNCE);
    return () => clearTimeout(timer);
  }, [module, configLoaded, widths, hiddenKeys]);

  const toggleColumnVisibility = useCallback(
    (columnKey) => {
      setHiddenKeys((prev) => {
        if (prev.includes(columnKey)) return prev.filter((key) => key !== columnKey);
        const remaining = safeColumns.filter(
          (column) => column.visible !== false && column.key !== columnKey && !prev.includes(column.key)
        );
        if (remaining.length === 0) return prev; // toujours au moins une colonne visible
        return [...prev, columnKey];
      });
    },
    [safeColumns]
  );

  const resetColumnPreferences = useCallback(() => {
    setWidths({});
    setHiddenKeys([]);
  }, []);

  // Fermeture du menu colonnes au clic extérieur / Échap.
  useEffect(() => {
    if (!showColumnMenu) return undefined;
    const onPointerDown = (event) => {
      if (columnMenuRef.current && !columnMenuRef.current.contains(event.target)) setShowColumnMenu(false);
    };
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setShowColumnMenu(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [showColumnMenu]);

  /* --------------------------------------------------- redimensionnement */

  const setColumnWidth = useCallback((columnKey, width) => {
    setWidths((prev) => {
      const next = clampWidth(width);
      if (prev[columnKey] === next) return prev;
      return { ...prev, [columnKey]: next };
    });
  }, []);

  const beginResize = useCallback(
    (columnKey, event) => {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      const column = columnMap.get(columnKey);
      resizeStateRef.current = {
        columnKey,
        startX: event.clientX,
        startWidth: column ? widthOf(column) : defaultColumnWidth,
        lastX: event.clientX,
      };
      setResizingKey(columnKey);
    },
    [columnMap, widthOf, defaultColumnWidth]
  );

  useEffect(() => {
    if (!resizingKey) return undefined;

    const handleMove = (event) => {
      const state = resizeStateRef.current;
      if (!state) return;
      state.lastX = event.clientX;
      if (resizeFrameRef.current) return; // throttle : une mise à jour par frame
      const schedule = typeof window.requestAnimationFrame === 'function'
        ? window.requestAnimationFrame
        : (cb) => setTimeout(cb, 16);
      resizeFrameRef.current = schedule(() => {
        resizeFrameRef.current = null;
        setColumnWidth(state.columnKey, state.startWidth + (state.lastX - state.startX));
      });
    };

    const handleUp = () => {
      const state = resizeStateRef.current;
      if (resizeFrameRef.current && typeof window.cancelAnimationFrame === 'function') {
        window.cancelAnimationFrame(resizeFrameRef.current);
        resizeFrameRef.current = null;
      }
      if (state) {
        setColumnWidth(state.columnKey, state.startWidth + (state.lastX - state.startX));
      }
      resizeStateRef.current = null;
      setResizingKey(null);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
    document.body.classList.add('dt-resizing-cursor');
    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
      document.body.classList.remove('dt-resizing-cursor');
      if (resizeFrameRef.current && typeof window.cancelAnimationFrame === 'function') {
        window.cancelAnimationFrame(resizeFrameRef.current);
        resizeFrameRef.current = null;
      }
    };
  }, [resizingKey, setColumnWidth]);

  const handleResizerKeyDown = useCallback(
    (columnKey, event) => {
      const column = columnMap.get(columnKey);
      if (!column) return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        setColumnWidth(columnKey, widthOf(column) - RESIZE_KEYBOARD_STEP);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        setColumnWidth(columnKey, widthOf(column) + RESIZE_KEYBOARD_STEP);
      } else if (event.key === 'Enter' || event.key === 'Backspace') {
        event.preventDefault();
        setWidths((prev) => {
          if (!(columnKey in prev)) return prev;
          const next = { ...prev };
          delete next[columnKey];
          return next;
        });
      }
    },
    [columnMap, setColumnWidth, widthOf]
  );

  const resetColumnWidth = useCallback((columnKey) => {
    setWidths((prev) => {
      if (!(columnKey in prev)) return prev;
      const next = { ...prev };
      delete next[columnKey];
      return next;
    });
  }, []);

  /* ------------------------------------------------------------ sélection */

  const resolveRowId = useCallback(
    (row, index) => {
      if (typeof rowKey === 'function') return rowKey(row, index);
      const value = row?.[rowKey];
      return isNil(value) ? `__row_${index}` : value;
    },
    [rowKey]
  );

  const sortedRows = useMemo(() => sortRows(rows, sortState, columnMap), [rows, sortState, columnMap]);

  const rowIds = useMemo(() => sortedRows.map((row, index) => resolveRowId(row, index)), [sortedRows, resolveRowId]);

  const rowsById = useMemo(() => {
    const map = new Map();
    sortedRows.forEach((row, index) => map.set(rowIds[index], row));
    return map;
  }, [sortedRows, rowIds]);

  const isSelectionControlled = Array.isArray(selectedIds);
  const selection = isSelectionControlled ? selectedIds : internalSelection;
  const selectionSet = useMemo(() => new Set(selection), [selection]);

  // Nettoyage de la sélection interne quand les données changent (suppression, refresh...).
  useEffect(() => {
    if (isSelectionControlled) return;
    setInternalSelection((prev) => {
      if (prev.length === 0) return prev;
      const available = new Set(rowIds);
      const next = prev.filter((id) => available.has(id));
      return next.length === prev.length ? prev : next;
    });
  }, [rowIds, isSelectionControlled]);

  const commitSelection = useCallback(
    (nextIds) => {
      if (!isSelectionControlled) setInternalSelection(nextIds);
      if (onSelectionChange) {
        onSelectionChange(nextIds, nextIds.map((id) => rowsById.get(id)).filter(Boolean));
      }
    },
    [isSelectionControlled, onSelectionChange, rowsById]
  );

  const handleToggleRow = useCallback(
    (rowId, index, event) => {
      const shiftKey = !!(event?.nativeEvent?.shiftKey || event?.shiftKey);
      const anchor = lastSelectedIndexRef.current;

      if (shiftKey && anchor !== null && anchor !== undefined && anchor !== index) {
        const start = Math.min(anchor, index);
        const end = Math.max(anchor, index);
        const rangeIds = rowIds.slice(start, end + 1);
        const shouldSelect = !selectionSet.has(rowId);
        const next = new Set(selectionSet);
        rangeIds.forEach((id) => (shouldSelect ? next.add(id) : next.delete(id)));
        lastSelectedIndexRef.current = index;
        commitSelection(Array.from(next));
        return;
      }

      lastSelectedIndexRef.current = index;
      const next = new Set(selectionSet);
      if (next.has(rowId)) next.delete(rowId);
      else next.add(rowId);
      commitSelection(Array.from(next));
    },
    [commitSelection, rowIds, selectionSet]
  );

  const allSelected = rowIds.length > 0 && rowIds.every((id) => selectionSet.has(id));
  const someSelected = !allSelected && rowIds.some((id) => selectionSet.has(id));

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = someSelected;
  }, [someSelected]);

  const handleToggleAll = useCallback(() => {
    lastSelectedIndexRef.current = null;
    if (allSelected) {
      const visible = new Set(rowIds);
      commitSelection(selection.filter((id) => !visible.has(id)));
    } else {
      commitSelection(Array.from(new Set([...selection, ...rowIds])));
    }
  }, [allSelected, commitSelection, rowIds, selection]);

  const clearSelection = useCallback(() => {
    lastSelectedIndexRef.current = null;
    commitSelection([]);
  }, [commitSelection]);

  const selectedRows = useMemo(
    () => selection.map((id) => rowsById.get(id)).filter(Boolean),
    [selection, rowsById]
  );

  const runBulkAction = useCallback(
    async (action) => {
      if (!action || typeof action.onClick !== 'function') return;
      if (action.confirm && typeof window !== 'undefined' && typeof window.confirm === 'function') {
        const message = typeof action.confirm === 'function' ? action.confirm(selection.length) : action.confirm;
        if (!window.confirm(message)) return;
      }
      try {
        setBusyBulkKey(action.key);
        await action.onClick(selection, selectedRows);
        if (action.clearSelection !== false) clearSelection();
      } finally {
        setBusyBulkKey(null);
      }
    },
    [clearSelection, selection, selectedRows]
  );

  /* ------------------------------------------------------- virtualisation */

  const virtualEnabled = useMemo(() => {
    if (virtualized === false) return false;
    if (virtualized === true) return true;
    return sortedRows.length > virtualizationThreshold;
  }, [virtualized, sortedRows.length, virtualizationThreshold]);

  const initialViewportHeight = useMemo(() => {
    const candidate = typeof height === 'number' ? height : typeof maxHeight === 'number' ? maxHeight : 520;
    return candidate > 0 ? candidate : 520;
  }, [height, maxHeight]);

  const virtualizer = useVirtualizer({
    count: virtualEnabled ? sortedRows.length : 0,
    getScrollElement: () => viewportRef.current,
    estimateSize: () => rowHeight,
    overscan,
    initialRect: { width: 0, height: initialViewportHeight },
  });

  const virtualItems = virtualEnabled ? virtualizer.getVirtualItems() : [];
  const totalVirtualSize = virtualEnabled ? virtualizer.getTotalSize() : 0;
  const paddingTop = virtualItems.length > 0 ? virtualItems[0].start : 0;
  const paddingBottom = virtualItems.length > 0
    ? Math.max(0, totalVirtualSize - virtualItems[virtualItems.length - 1].end)
    : 0;

  /* ----------------------------------------------------------- rendu ligne */

  const rowStyle = useMemo(
    () => (virtualEnabled ? { height: `${rowHeight}px` } : undefined),
    [virtualEnabled, rowHeight]
  );

  const columnCount = visibleColumns.length + (selectable ? 1 : 0) + 1; // +1 = colonne tampon

  const renderRow = useCallback(
    (row, index) => {
      const rowId = rowIds[index];
      return (
        <DataTableRow
          key={rowId}
          row={row}
          rowId={rowId}
          index={index}
          columns={visibleColumns}
          selectable={selectable}
          selected={selectionSet.has(rowId)}
          onToggleRow={handleToggleRow}
          onRowClick={onRowClick}
          rowStyle={rowStyle}
          className={typeof rowClassName === 'function' ? rowClassName(row, index) : rowClassName}
        />
      );
    },
    [rowIds, visibleColumns, selectable, selectionSet, handleToggleRow, onRowClick, rowStyle, rowClassName]
  );

  const sortIndexOf = useCallback((columnKey) => sortState.findIndex((entry) => entry.key === columnKey), [sortState]);

  const hasBulkActions = selectable && Array.isArray(bulkActions) && bulkActions.length > 0;
  const showToolbar = !!(title || toolbar || columnToggle);
  const isEmpty = sortedRows.length === 0;

  return (
    <div
      className={['dt-root', dense ? 'dt-root--dense' : '', resizingKey ? 'is-resizing' : '', className || '']
        .filter(Boolean)
        .join(' ')}
    >
      {showToolbar && (
        <div className="dt-toolbar">
          <div className="dt-toolbar-left">
            {title && <h3 className="dt-title">{title}</h3>}
            {toolbar}
          </div>
          <div className="dt-toolbar-right">
            {columnToggle && (
              <div className="dt-column-menu" ref={columnMenuRef}>
                <button
                  type="button"
                  className="dt-toolbar-btn"
                  onClick={() => setShowColumnMenu((open) => !open)}
                  aria-expanded={showColumnMenu}
                  aria-haspopup="true"
                >
                  <i className="ti ti-columns" aria-hidden="true" />
                  <span>Colonnes</span>
                  {hiddenKeys.length > 0 && <span className="dt-toolbar-badge">{hiddenKeys.length}</span>}
                </button>
                {showColumnMenu && (
                  <div className="dt-column-dropdown" role="menu">
                    {safeColumns.map((column) => (
                      <label key={column.key} className="dt-column-option">
                        <input
                          type="checkbox"
                          checked={!hiddenKeys.includes(column.key) && column.visible !== false}
                          onChange={() => toggleColumnVisibility(column.key)}
                        />
                        <span>{column.label || column.key}</span>
                      </label>
                    ))}
                    <button type="button" className="dt-column-reset" onClick={resetColumnPreferences}>
                      <i className="ti ti-arrow-back-up" aria-hidden="true" /> Réinitialiser colonnes
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {hasBulkActions && selection.length > 0 && (
        <div className="dt-bulkbar" role="toolbar" aria-label="Actions groupées">
          <span className="dt-bulkbar-count">
            <i className="ti ti-checkbox" aria-hidden="true" />
            <strong>{selection.length}</strong>
            {selection.length > 1 ? ' lignes sélectionnées' : ' ligne sélectionnée'}
          </span>
          <div className="dt-bulkbar-actions">
            {bulkActions.map((action) => (
              <button
                key={action.key}
                type="button"
                className={`dt-bulk-btn${action.variant === 'danger' ? ' is-danger' : ''}`}
                onClick={() => runBulkAction(action)}
                disabled={action.disabled || busyBulkKey !== null}
              >
                {busyBulkKey === action.key ? (
                  <span className="dt-spinner" aria-hidden="true" />
                ) : (
                  action.icon && <i className={`ti ${action.icon}`} aria-hidden="true" />
                )}
                <span>{action.label}</span>
              </button>
            ))}
            <button type="button" className="dt-bulk-btn is-ghost" onClick={clearSelection}>
              Tout désélectionner
            </button>
          </div>
        </div>
      )}

      <div
        ref={viewportRef}
        className={`dt-viewport${virtualEnabled ? ' is-virtual' : ''}`}
        style={{ height: height || undefined, maxHeight: height ? undefined : maxHeight }}
      >
        <table className="dt-table" style={{ minWidth: totalWidth }}>
          <colgroup>
            {selectable && <col style={{ width: SELECTION_COLUMN_WIDTH }} />}
            {visibleColumns.map((column) => (
              <col key={column.key} style={{ width: widthOf(column) }} />
            ))}
            <col className="dt-filler-col" />
          </colgroup>
          <thead>
            <tr>
              {selectable && (
                <th className="dt-th dt-th--select" scope="col">
                  <input
                    ref={selectAllRef}
                    type="checkbox"
                    checked={allSelected}
                    onChange={handleToggleAll}
                    disabled={rowIds.length === 0}
                    aria-label="Sélectionner toutes les lignes"
                  />
                </th>
              )}
              {visibleColumns.map((column) => {
                const sortIndex = sortIndexOf(column.key);
                const direction = sortIndex >= 0 ? sortState[sortIndex].direction : null;
                const sortable = column.sortable !== false;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    className={[
                      'dt-th',
                      sortable ? 'is-sortable' : '',
                      sortIndex >= 0 ? 'is-sorted' : '',
                      column.align ? `dt-align-${column.align}` : '',
                      column.headerClassName || '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    aria-sort={sortIndex >= 0 ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        className="dt-th-btn"
                        onClick={(event) => handleSortClick(column.key, event)}
                        title={
                          multiSort
                            ? `${column.label || column.key} — clic : trier · Maj+clic : tri multi-critères`
                            : `${column.label || column.key} — clic : trier`
                        }
                      >
                        <span className="dt-th-label">{column.label || column.key}</span>
                        <span className="dt-sort-icon" aria-hidden="true">
                          {direction === 'asc' ? '▲' : direction === 'desc' ? '▼' : '↕'}
                        </span>
                        {sortState.length > 1 && sortIndex >= 0 && (
                          <span className="dt-sort-rank" aria-hidden="true">
                            {sortIndex + 1}
                          </span>
                        )}
                      </button>
                    ) : (
                      <span className="dt-th-label dt-th-label--static">{column.label || column.key}</span>
                    )}
                    {resizable && column.resizable !== false && (
                      <span
                        role="separator"
                        tabIndex={0}
                        aria-orientation="vertical"
                        aria-label={`Redimensionner la colonne ${column.label || column.key}`}
                        className={`dt-resizer${resizingKey === column.key ? ' is-active' : ''}`}
                        data-resizer={column.key}
                        onMouseDown={(event) => beginResize(column.key, event)}
                        onDoubleClick={() => resetColumnWidth(column.key)}
                        onKeyDown={(event) => handleResizerKeyDown(column.key, event)}
                      />
                    )}
                  </th>
                );
              })}
              <th className="dt-th dt-th--filler" aria-hidden="true" />
            </tr>
          </thead>
          <tbody>
            {isEmpty ? (
              <tr className="dt-row dt-row--empty">
                <td colSpan={columnCount} className="dt-empty">
                  {loading ? 'Chargement…' : emptyMessage}
                </td>
              </tr>
            ) : virtualEnabled ? (
              <>
                {paddingTop > 0 && (
                  <tr className="dt-spacer" aria-hidden="true" style={{ height: `${paddingTop}px` }}>
                    <td colSpan={columnCount} />
                  </tr>
                )}
                {virtualItems.map((virtualRow) => renderRow(sortedRows[virtualRow.index], virtualRow.index))}
                {paddingBottom > 0 && (
                  <tr className="dt-spacer" aria-hidden="true" style={{ height: `${paddingBottom}px` }}>
                    <td colSpan={columnCount} />
                  </tr>
                )}
              </>
            ) : (
              sortedRows.map((row, index) => renderRow(row, index))
            )}
          </tbody>
        </table>
        {loading && !isEmpty && (
          <div className="dt-loading-overlay" aria-live="polite">
            <span className="dt-spinner" aria-hidden="true" />
            <span>Chargement…</span>
          </div>
        )}
      </div>

      {showFooter && (
        <div className="dt-footer">
          <span className="dt-footer-count">
            {sortedRows.length} ligne{sortedRows.length > 1 ? 's' : ''}
            {selectable && selection.length > 0 ? ` · ${selection.length} sélectionnée${selection.length > 1 ? 's' : ''}` : ''}
          </span>
          <span className="dt-footer-tags">
            {sortState.length > 1 && (
              <span className="dt-footer-tag">
                Tri multi-critères : {sortState.map((entry) => `${columnMap.get(entry.key)?.label || entry.key} ${entry.direction === 'asc' ? '↑' : '↓'}`).join(' › ')}
              </span>
            )}
            {virtualEnabled && (
              <span className="dt-footer-tag" data-testid="dt-virtual-tag">
                Virtualisation active · {virtualItems.length} lignes rendues
              </span>
            )}
          </span>
        </div>
      )}
    </div>
  );
};

export default DataTable;
