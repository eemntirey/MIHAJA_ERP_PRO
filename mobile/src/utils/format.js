// src/utils/format.js
// Helpers de formatage (sans Intl, compatible Hermes).

// 1234567 → "1 234 567"
export const formatNumber = (value) => {
  const n = Math.round(Number(value) || 0);
  const sign = n < 0 ? '-' : '';
  return sign + String(Math.abs(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
};

// Montants en Ariary : 1234.5 → "1 235 Ar"
export const formatMoney = (value) => `${formatNumber(value)} Ar`;

// "2026-09-11T08:30:00" → "11/09/2026 08:30"
export const formatDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const pad = (v) => String(v).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// "2026-09-11T08:30:00" → "11/09/2026"
export const formatDateOnly = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const pad = (v) => String(v).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
};

// "Jean Rakoto" → "JR"
export const initials = (name) => {
  if (!name) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('') || '?';
};
