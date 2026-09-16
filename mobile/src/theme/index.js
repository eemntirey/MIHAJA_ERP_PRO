// src/theme/index.js
// Thème mobile aligné sur le Design System MIHAJA ERP PRO (Web + Desktop)
// Senior UX : tokens cohérents, contraste élevé, typographie fluide, ombres colorées.

export const colors = {
  primary: '#d4af37',         // Or marque — même que --color-primary web/desk
  primaryHover: '#cda233',     // Gold-600
  primaryActive: '#b48c2a',    // Gold-700
  primarySoft: '#fefce8',      // Gold-50
  primaryRing: 'rgba(212, 175, 55, 0.35)',

  surface: '#ffffff',
  surfaceElevated: '#ffffff',
  surfaceHover: '#f5f5f4',     // Neutral-100
  surfaceActive: '#fafafa',     // Neutral-50

  background: '#fafafa',        // Neutral-50 — même que --color-background

  border: '#e7e5e4',           // Neutral-200
  borderStrong: '#d6d3d1',     // Neutral-300
  borderSubtle: '#f5f5f4',     // Neutral-100

  text: '#0c0a09',             // Neutral-950 — contraste senior
  textSecondary: '#57534e',    // Neutral-600
  textTertiary: '#78716c',     // Neutral-500
  textMuted: '#a8a29e',        // Neutral-400
  textInverse: '#ffffff',
  textDisabled: '#d6d3d1',     // Neutral-300

  success: '#22c55e',          // Green-500
  successSoft: '#f0fdf4',       // Green-50 — même que --color-success-soft
  successBg: '#f0fdf4',         // Alias utilisé par Badge/States
  successText: '#14532d',

  warning: '#f59e0b',          // Amber-500
  warningSoft: '#fffbeb',       // Amber-50 — même que --color-warning-soft
  warningBg: '#fffbeb',         // Alias utilisé par Badge/States
  warningText: '#78350f',

  danger: '#ef4444',           // Red-500
  dangerSoft: '#fef2f2',        // Red-50 — même que --color-danger-soft
  dangerBg: '#fef2f2',          // Alias utilisé par Badge/States
  dangerText: '#7f1d1d',

  info: '#3b82f6',             // Blue-500
  infoSoft: '#eff6ff',          // Blue-50 — même que --color-info-soft
  infoBg: '#eff6ff',            // Alias utilisé par Badge/States
  infoText: '#1e3a8a',

  // Fond translucide "primary tint" — même rendu que rgba(212,175,55,0.14) web
  primaryTint: 'rgba(212, 175, 55, 0.14)',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const radius = {
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  '2xl': 20,
  pill: 999,
};

export const shadow = {
  xs: '0 1px 2px rgba(15, 23, 42, 0.06)',
  sm: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
  md: '0 4px 12px rgba(15, 23, 42, 0.08), 0 2px 4px rgba(15, 23, 42, 0.04)',
  lg: '0 12px 32px rgba(15, 23, 42, 0.10), 0 4px 12px rgba(15, 23, 42, 0.06)',
  primarySm: '0 2px 8px rgba(212, 175, 55, 0.25)',
  primaryMd: '0 8px 24px rgba(212, 175, 55, 0.3)',
  primaryLg: '0 16px 40px rgba(212, 175, 55, 0.35)',
};

export const fontSizes = {
  micro: 10,
  caption: 11,
  label: 12,
  bodySm: 13,
  body: 14,
  bodyLg: 16,
  h4: 16,
  h3: 18,
  h2: 22,
  h1: 28,
  display: 32,
  kpiSm: 20,
  kpi: 28,
  kpiLg: 36,

  // Alias sémantiques (utilisés par les composants) — alignés sur l'échelle
  // typographique senior du Design System web (tokens.css / typography.css).
  xs: 11,   // caption — badges, métadonnées, erreurs de champ
  sm: 13,   // bodySm — textes secondaires, labels, sous-titres
  md: 16,   // bodyLg — texte interactif (boutons, inputs) : lisibilité senior
  lg: 20,   // kpiSm — valeurs de cartes statistiques
  xl: 22,   // h2 — titres d'écran et de modales
};

export const fontWeights = {
  normal: '400',
  medium: '500',
  semibold: '600',
  bold: '700',
  extrabold: '800',
};

export const duration = {
  fast: 120,
  normal: 180,
  slow: 240,
  slower: 320,
};

export const zIndex = {
  base: 1,
  sticky: 50,
  dropdown: 40,
  overlay: 100,
  modal: 200,
  tooltip: 400,
  toast: 500,
};
