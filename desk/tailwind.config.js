/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--bg-primary)',
        foreground: 'var(--text-primary)',
        card: 'var(--card-bg)',
        'card-foreground': 'var(--text-primary)',
        primary: {
          DEFAULT: 'var(--erp-gold)',
          foreground: 'var(--erp-onyx)',
        },
        secondary: {
          DEFAULT: 'var(--bg-secondary)',
          foreground: 'var(--text-primary)',
        },
        muted: {
          DEFAULT: 'var(--erp-muted)',
          foreground: 'var(--text-secondary)',
        },
        accent: {
          DEFAULT: 'var(--erp-gold)',
          foreground: 'var(--erp-onyx)',
        },
        destructive: {
          DEFAULT: 'var(--erp-critical)',
          foreground: '#ffffff',
        },
        border: 'var(--border-color)',
        input: 'var(--border-color)',
        ring: 'var(--erp-gold)',
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      fontFamily: {
        sans: ['var(--erp-body-font)', 'sans-serif'],
        heading: ['var(--erp-heading-font)', 'sans-serif'],
      },
      borderRadius: {
        lg: '0.5rem',
        md: 'calc(0.5rem - 2px)',
        sm: 'calc(0.5rem - 4px)',
      },
    },
  },
  plugins: [],
};
