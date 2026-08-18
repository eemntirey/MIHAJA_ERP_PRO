const numberFormatter = new Intl.NumberFormat('mg-MG', {
  maximumFractionDigits: 0,
});

const currencyFormatter = new Intl.NumberFormat('mg-MG', {
  style: 'currency',
  currency: 'MGA',
  maximumFractionDigits: 0,
});

const exactCurrencyFormatter = new Intl.NumberFormat('mg-MG', {
  style: 'currency',
  currency: 'MGA',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const axisCurrencyFormatter = new Intl.NumberFormat('mg-MG', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

const dateFormatter = new Intl.DateTimeFormat('mg-MG', {
  day: '2-digit',
  month: 'short',
});

const chartDateFormatter = new Intl.DateTimeFormat('mg-MG', {
  weekday: 'short',
  day: '2-digit',
});

const timeFormatter = new Intl.DateTimeFormat('mg-MG', {
  hour: '2-digit',
  minute: '2-digit',
});

const monthYearFormatter = new Intl.DateTimeFormat('mg-MG', {
  month: 'long',
  year: 'numeric',
});

export const toNumber = (value, fallback = 0) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value.replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  return fallback;
};

export const formatNumber = (value) => numberFormatter.format(toNumber(value));

export const formatCurrency = (value) => currencyFormatter.format(toNumber(value));

export const formatCurrencyExact = (value) => exactCurrencyFormatter.format(toNumber(value));

export const formatCompactCurrency = (value) => {
  const amount = toNumber(value);
  if (Math.abs(amount) >= 1000) {
    const compact = amount / 1000;
    const decimals = Math.abs(compact) >= 10 ? 0 : 1;
    return `${compact.toFixed(decimals).replace('.', ',')}k Ar`;
  }

  return `${numberFormatter.format(amount)} Ar`;
};

export const formatChartAxisCurrency = (value) => {
  const amount = toNumber(value);
  if (Math.abs(amount) >= 1000) {
    return formatCompactCurrency(amount);
  }

  return `${axisCurrencyFormatter.format(amount)} Ar`;
};

export const getSaleDate = (sale) => sale?.date || sale?.created_at || null;

export const getDateKey = (value) => {
  if (!value) return null;

  const rawValue = String(value);
  const isoDate = rawValue.match(/^\d{4}-\d{2}-\d{2}/);
  if (isoDate) return isoDate[0];

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const dateFromKey = (dateKey) => {
  if (!dateKey) return null;
  const date = new Date(`${dateKey}T12:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
};

const addDays = (date, amount) => {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + amount);
  return nextDate;
};

export const formatDateLabel = (dateKey) => {
  const date = dateFromKey(dateKey);
  if (!date) return 'Date inconnue';

  return dateFormatter.format(date).replace('.', '');
};

export const formatChartDateLabel = (dateKey) => {
  const date = dateFromKey(dateKey);
  if (!date) return 'Date inconnue';

  return chartDateFormatter.format(date).replace('.', '');
};

export const formatDateRange = (startKey, endKey) => {
  const start = dateFromKey(startKey);
  const end = dateFromKey(endKey);
  if (!start || !end) return 'Période indisponible';

  const startLabel = dateFormatter.format(start).replace('.', '');
  const endLabel = dateFormatter.format(end).replace('.', '');
  return `${startLabel} — ${endLabel}`;
};

export const formatMonthYear = (dateKey) => {
  const date = dateFromKey(dateKey);
  if (!date) return 'Période indisponible';

  const label = monthYearFormatter.format(date);
  return label.charAt(0).toUpperCase() + label.slice(1);
};

export const getSevenDayKeys = (endDate = new Date()) => {
  return Array.from({ length: 7 }, (_, index) => getDateKey(addDays(endDate, index - 6)));
};

export const buildSalesEvolution = (sales = [], endDate = new Date()) => {
  const keys = getSevenDayKeys(endDate);
  const salesByDay = new Map(keys.map((key) => [key, { total: 0, count: 0 }]));

  sales.forEach((sale) => {
    const dateKey = getDateKey(getSaleDate(sale));
    if (!salesByDay.has(dateKey)) return;

    const current = salesByDay.get(dateKey);
    current.total += toNumber(sale.total_ttc);
    current.count += 1;
  });

  return keys.map((dateKey) => ({
    dateKey,
    label: formatChartDateLabel(dateKey),
    total: salesByDay.get(dateKey).total,
    count: salesByDay.get(dateKey).count,
  }));
};

export const buildPreviousPeriodTotal = (sales = [], endDate = new Date()) => {
  const currentStart = addDays(endDate, -6);
  const previousKeys = Array.from({ length: 7 }, (_, index) =>
    getDateKey(addDays(currentStart, index - 7))
  );
  const previousKeySet = new Set(previousKeys);

  const matchingSales = sales.filter((sale) => previousKeySet.has(getDateKey(getSaleDate(sale))));
  if (matchingSales.length === 0) return null;

  return matchingSales.reduce((total, sale) => total + toNumber(sale.total_ttc), 0);
};

export const getTodayTotal = (sales = [], today = new Date()) => {
  const todayKey = getDateKey(today);
  const todaySales = sales.filter((sale) => getDateKey(getSaleDate(sale)) === todayKey);

  if (todaySales.length === 0) {
    return sales.length === 0 ? null : 0;
  }

  return todaySales.reduce((total, sale) => total + toNumber(sale.total_ttc), 0);
};

export const formatActivityTime = (value, now = new Date()) => {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '—';

  if (getDateKey(date) === getDateKey(now)) {
    return timeFormatter.format(date);
  }

  return dateFormatter.format(date).replace('.', '');
};

export const formatPercentageChange = (current, previous) => {
  const currentValue = toNumber(current, null);
  const previousValue = toNumber(previous, null);

  if (currentValue === null || previousValue === null || previousValue <= 0) {
    return null;
  }

  return ((currentValue - previousValue) / previousValue) * 100;
};

export const formatTrendLabel = (percentage) => {
  if (percentage === null || percentage === undefined) return 'Pas de comparaison';
  const sign = percentage > 0 ? '+' : '';
  return `${sign}${percentage.toFixed(1).replace('.', ',')} %`;
};

export const normalizeTopProducts = (responseData = {}) => {
  const products = responseData.top_products || responseData.top_produits || [];

  return products.slice(0, 5).map((product, index) => ({
    id: product.produit_id || product.id || `product-${index}`,
    name: product.nom || 'Produit sans nom',
    quantity: toNumber(product.total_quantite),
    value: toNumber(product.total_ca ?? product.total_ttc),
  }));
};

export const normalizeRecentActivity = (sales = []) => {
  const sortedSales = [...sales]
    .filter((sale) => getSaleDate(sale))
    .sort((first, second) => new Date(getSaleDate(second)) - new Date(getSaleDate(first)))
    .slice(0, 4);

  return sortedSales.map((sale, index) => {
    const saleReference = sale.reference || sale.id || `vente-${index + 1}`;
    const saleStatus = String(sale.statut || '').toLowerCase();
    const title = saleStatus === 'annulee'
      ? `Vente #${saleReference} annulée`
      : `Vente #${saleReference} enregistrée`;

    return {
      id: sale.id || saleReference,
      title,
      meta: `Montant · ${formatCurrencyExact(sale.total_ttc)}`,
      timeLabel: formatActivityTime(getSaleDate(sale)),
      tone: index < 2 ? 'active' : 'muted',
    };
  });
};

export const normalizeCriticalStockAlerts = (responseData) => {
  if (!Array.isArray(responseData?.alertes_stock)) return null;

  return responseData.alertes_stock.filter((product) => {
    const quantity = toNumber(product.quantite_stock);
    const criticalThreshold = toNumber(product.seuil_critique, 0);
    return quantity <= criticalThreshold;
  }).length;
};

export const normalizeReceivables = (dashboardData = {}) => {
  const receivables = Array.isArray(dashboardData.creances_clients)
    ? dashboardData.creances_clients
    : [];

  return {
    count: receivables.length,
    total: receivables.reduce((total, item) => total + toNumber(item.creance), 0),
  };
};

export const buildPriorities = ({
  criticalStockAlerts,
  stockAlerts,
  receivablesCount,
  todaySales,
  hasSalesData,
}) => {
  const priorities = [];

  if (criticalStockAlerts > 0) {
    priorities.push({
      id: 'critical-stock',
      title: 'Réassort critique',
      description: `${formatNumber(criticalStockAlerts)} référence(s) sous le seuil critique.`,
      href: '/inventory',
      icon: 'ti-alert-circle',
      tone: 'critical',
    });
  } else if (criticalStockAlerts === null && stockAlerts > 0) {
    priorities.push({
      id: 'stock-watch',
      title: 'Surveiller le stock',
      description: `${formatNumber(stockAlerts)} alerte(s) à examiner dans l’inventaire.`,
      href: '/inventory',
      icon: 'ti-box',
      tone: 'gold',
    });
  }

  if (receivablesCount > 0) {
    priorities.push({
      id: 'receivables',
      title: 'Créances à relancer',
      description: `${formatNumber(receivablesCount)} client(s) présentent un solde à suivre.`,
      href: '/invoices',
      icon: 'ti-file-invoice',
      tone: 'gold',
    });
  }

  if (hasSalesData && todaySales === 0) {
    priorities.push({
      id: 'sales-review',
      title: 'Analyser les ventes',
      description: 'Aucune vente enregistrée aujourd’hui dans les données chargées.',
      href: '/sales',
      icon: 'ti-chart-line',
      tone: 'neutral',
    });
  }

  if (priorities.length === 0) {
    priorities.push({
      id: 'operations-clear',
      title: 'Activité sous contrôle',
      description: 'Aucune priorité opérationnelle détectée pour le moment.',
      href: '/dashboard',
      icon: 'ti-circle-check',
      tone: 'neutral',
    });
  }

  return priorities.slice(0, 3);
};

const getNiceAxisMax = (value) => {
  const safeValue = Math.max(toNumber(value), 1);
  const magnitude = 10 ** Math.floor(Math.log10(safeValue));
  const normalized = safeValue / magnitude;
  const niceNormalized = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return niceNormalized * magnitude;
};

export const buildChartGeometry = (evolution = []) => {
  const width = 1000;
  const top = 24;
  const bottom = 232;
  const left = 70;
  const right = 946;
  const axisMax = getNiceAxisMax(Math.max(...evolution.map((day) => day.total), 0));
  const xStep = evolution.length > 1 ? (right - left) / (evolution.length - 1) : 0;

  const points = evolution.map((day, index) => ({
    ...day,
    x: left + xStep * index,
    y: bottom - (toNumber(day.total) / axisMax) * (bottom - top),
  }));

  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x} ${point.y}`).join(' ');
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];
  const areaPath = points.length > 0
    ? `${linePath} L${lastPoint.x} ${bottom} L${firstPoint.x} ${bottom} Z`
    : '';

  const grid = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    return {
      y: top + ratio * (bottom - top),
      label: formatChartAxisCurrency(axisMax * (1 - ratio)),
    };
  });

  const bestIndex = evolution.length > 0
    ? evolution.reduce((best, day, index, allDays) => (
      day.total > allDays[best].total ? index : best
    ), 0)
    : -1;

  return {
    width,
    height: 260,
    left,
    right,
    top,
    bottom,
    points,
    linePath,
    areaPath,
    grid,
    axisMax,
    bestIndex: evolution[bestIndex]?.total > 0 ? bestIndex : -1,
  };
};

export const buildSparklinePath = (values = []) => {
  const totals = values.map((value) => toNumber(value));
  if (totals.length < 2 || Math.max(...totals) === 0) {
    return 'M2 52 L126 52';
  }

  const max = Math.max(...totals, 1);
  const step = 124 / (totals.length - 1);
  return totals
    .map((total, index) => {
      const x = 2 + step * index;
      const y = 56 - (total / max) * 48;
      return `${index === 0 ? 'M' : 'L'}${x} ${y}`;
    })
    .join(' ');
};

const csvEscape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;

export const serializeDashboardCsv = ({ stats, evolution, topProducts, recentActivity }) => {
  const rows = [
    ['Section', 'Indicateur', 'Valeur'],
    ['Synthèse', 'Chiffre d’affaires du mois', formatCurrencyExact(stats.revenue)],
    ['Synthèse', 'Produits', stats.products],
    ['Synthèse', 'Clients', stats.clients],
    ['Synthèse', 'Ventes aujourd’hui', stats.salesToday],
    ['Synthèse', 'Alertes stock', stats.stockAlerts],
    ['Synthèse', 'Alertes critiques', stats.criticalStockAlerts ?? 'Non disponible'],
    ['Évolution', 'Date', 'Chiffre d’affaires'],
    ...evolution.map((day) => ['Évolution', day.dateKey, formatCurrencyExact(day.total)]),
    ['Top produits', 'Produit', 'Quantité', 'Valeur'],
    ...topProducts.map((product) => ['Top produits', product.name, product.quantity, formatCurrencyExact(product.value)]),
    ['Activité', 'Événement', 'Détail', 'Heure'],
    ...recentActivity.map((item) => ['Activité', item.title, item.meta, item.timeLabel]),
  ];

  return rows.map((row) => row.map(csvEscape).join(';')).join('\n');
};
