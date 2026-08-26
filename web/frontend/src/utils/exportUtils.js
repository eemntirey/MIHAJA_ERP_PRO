// src/utils/exportUtils.js
// Export CSV local (aucun appel réseau) — utilisé par les actions groupées du DataTable.

const SEPARATOR = ';'; // séparateur attendu par Excel en configuration FR

const escapeCell = (value) => {
  if (value === null || value === undefined) return '';
  const text = value instanceof Date ? value.toISOString() : String(value);
  if (text.includes('"') || text.includes(SEPARATOR) || /[\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
};

/** Valeur exportable d'une cellule : `exportValue` > `sortAccessor` > `accessor` > row[key]. */
export const resolveExportValue = (column, row) => {
  if (typeof column.exportValue === 'function') return column.exportValue(row);
  if (typeof column.sortAccessor === 'function') return column.sortAccessor(row);
  if (typeof column.accessor === 'function') return column.accessor(row);
  return row?.[column.key];
};

/**
 * Construit le contenu CSV.
 * @param {Array<{key:string,label?:string}>} columns
 * @param {Array<Object>} rows
 */
export const buildCsv = (columns, rows) => {
  const exportable = (columns || []).filter((col) => col && col.key && col.exportable !== false);
  const header = exportable.map((col) => escapeCell(col.label || col.key)).join(SEPARATOR);
  const body = (rows || [])
    .map((row) => exportable.map((col) => escapeCell(resolveExportValue(col, row))).join(SEPARATOR))
    .join('\r\n');
  return body ? `${header}\r\n${body}` : header;
};

/**
 * Déclenche le téléchargement d'un CSV.
 * @returns {boolean} false si l'environnement ne supporte pas le téléchargement.
 */
export const exportRowsToCsv = (filename, columns, rows) => {
  const csv = buildCsv(columns, rows);
  if (typeof document === 'undefined' || typeof URL === 'undefined' || !URL.createObjectURL) return false;
  try {
    // BOM UTF-8 pour préserver les accents à l'ouverture dans Excel.
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 0);
    return true;
  } catch {
    return false;
  }
};

/** Nom de fichier horodaté : ventes-2026-08-18-1930.csv */
export const timestampedFilename = (prefix) => {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${prefix}-${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}.csv`;
};
