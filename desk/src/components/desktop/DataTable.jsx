// src/components/desktop/DataTable.jsx
import React, { useState, useMemo, useCallback } from 'react';
import './DataTable.css';

const DataTable = ({
  columns,
  data,
  onRowClick,
  onSort,
  sortConfig,
  selectedRows,
  onSelectRow,
  onSelectAll,
  onColumnResize,
  columnWidths,
  onColumnVisibilityChange,
  visibleColumns: externalVisibleColumns,
}) => {
  const [internalSort, setInternalSort] = useState({ key: null, direction: 'asc', multi: [] });
  const [hoveredCol, setHoveredCol] = useState(null);
  const [showColumnMenu, setShowColumnMenu] = useState(false);

  const effectiveSort = sortConfig || internalSort;

  const handleSortClick = useCallback((key, e) => {
    let newSort;
    if (e.shiftKey) {
      const existing = effectiveSort.multi?.find((s) => s.key === key);
      if (existing) {
        const newMulti = effectiveSort.multi.map((s) =>
          s.key === key ? { ...s, direction: s.direction === 'asc' ? 'desc' : 'asc' } : s
        );
        newSort = { ...effectiveSort, multi: newMulti };
      } else {
        newSort = { ...effectiveSort, multi: [...(effectiveSort.multi || []), { key, direction: 'asc' }] };
      }
    } else {
      newSort = effectiveSort.key === key
        ? { key, direction: effectiveSort.direction === 'asc' ? 'desc' : 'asc', multi: [] }
        : { key, direction: 'asc', multi: [] };
    }
    if (onSort) onSort(newSort);
    else setInternalSort(newSort);
  }, [effectiveSort, onSort]);

  const getSortIndicator = (key) => {
    if (!effectiveSort) return '';
    if (effectiveSort.key === key) return effectiveSort.direction === 'asc' ? ' ▲' : ' ▼';
    const multiItem = effectiveSort.multi?.find((s) => s.key === key);
    if (multiItem) return multiItem.direction === 'asc' ? ' ▲' : ' ▼';
    return '';
  };

  const visibleColumns = useMemo(() => {
    if (externalVisibleColumns) return externalVisibleColumns;
    return columns.filter((c) => c.visible !== false);
  }, [columns, externalVisibleColumns]);

  const sortedData = useMemo(() => {
    if (!effectiveSort || !effectiveSort.key) return data;
    const keys = [effectiveSort.key, ...(effectiveSort.multi || []).map((s) => s.key)];
    const directions = {};
    directions[effectiveSort.key] = effectiveSort.direction;
    effectiveSort.multi?.forEach((s) => { directions[s.key] = s.direction; });

    return [...data].sort((a, b) => {
      for (const key of keys) {
        const dir = directions[key] || 'asc';
        const aVal = a[key];
        const bVal = b[key];
        if (aVal === bVal) continue;
        const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        return dir === 'asc' ? cmp : -cmp;
      }
      return 0;
    });
  }, [data, effectiveSort]);

  const toggleColumnVisibility = useCallback((colKey) => {
    if (onColumnVisibilityChange) onColumnVisibilityChange(colKey);
  }, [onColumnVisibilityChange]);

  return (
    <div className="data-table-wrapper">
      <div className="data-table-toolbar">
        {onColumnVisibilityChange && (
          <div className="data-table-column-menu">
            <button className="data-table-column-toggle" onClick={() => setShowColumnMenu(!showColumnMenu)}>
              <i className="ti ti-settings" aria-hidden="true" /> Colonnes
            </button>
            {showColumnMenu && (
              <div className="data-table-column-dropdown">
                {columns.map((col) => (
                  <label key={col.key} className="data-table-column-option">
                    <input
                      type="checkbox"
                      checked={visibleColumns.some((vc) => vc.key === col.key)}
                      onChange={() => toggleColumnVisibility(col.key)}
                    />
                    <span>{col.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="data-table-scroll">
        <table className="data-table desktop-data-table">
          <thead>
            <tr>
              {onSelectAll && (
                <th className="dt-col dt-col--check" style={{ width: 40 }}>
                  <input
                    type="checkbox"
                    checked={selectedRows?.length === data.length && data.length > 0}
                    onChange={(e) => onSelectAll(e.target.checked)}
                  />
                </th>
              )}
              {visibleColumns.map((col) => (
                <th
                  key={col.key}
                  className={`dt-col ${col.sortable ? 'sortable' : ''}`}
                  style={{ width: columnWidths?.[col.key] || col.width || 'auto' }}
                  onMouseEnter={() => setHoveredCol(col.key)}
                  onMouseLeave={() => setHoveredCol(null)}
                  onClick={(e) => col.sortable && handleSortClick(col.key, e)}
                >
                  <div className="dt-th-content">
                    <span>{col.label}</span>
                    {col.sortable && <span className="dt-sort-indicator">{getSortIndicator(col.key)}</span>}
                  </div>
                  {onColumnResize && hoveredCol === col.key && (
                    <div className="dt-col-resizer" onMouseDown={(e) => onColumnResize(col.key, e)} />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.length === 0 ? (
              <tr>
                <td colSpan={visibleColumns.length + (onSelectAll ? 1 : 0)} className="dt-empty">
                  Aucune donnée
                </td>
              </tr>
            ) : (
              sortedData.map((row, rowIndex) => (
                <tr
                  key={row.id || rowIndex}
                  className={onRowClick ? 'clickable' : ''}
                  onClick={() => onRowClick?.(row)}
                >
                  {onSelectAll && (
                    <td className="dt-col dt-col--check">
                      <input
                        type="checkbox"
                        checked={selectedRows?.includes(row.id)}
                        onChange={() => onSelectRow(row.id)}
                      />
                    </td>
                  )}
                  {visibleColumns.map((col) => (
                    <td key={col.key} className="dt-col" style={{ width: columnWidths?.[col.key] || col.width || 'auto' }}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;
