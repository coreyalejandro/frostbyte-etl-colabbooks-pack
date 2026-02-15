/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#0a0c0e',
        surface: '#1c1f22',
        'surface-elevated': '#24282c',
        interactive: '#2c3035',
        border: '#3c4045',
        inactive: '#5f6368',
        'text-secondary': '#9aa0a6',
        'text-primary': '#e8eaed',
        'text-tertiary': '#6c7278',
        accent: '#fbbf24', // Changed from #eab308 to meet WCAG AA 4.5:1 contrast ratio on dark backgrounds
        // Semantic colors for status indicators (WCAG AA on dark backgrounds)
        green: {
          400: '#4ade80', // High contrast on dark - connected/healthy
          500: '#22c55e',
        },
        red: {
          400: '#f87171', // High contrast on dark - errors/failures
          500: '#ef4444',
        },
        blue: {
          400: '#60a5fa', // High contrast on dark - processing/in-progress
          500: '#3b82f6',
        },
      },
      fontFamily: {
        mono: ['IBM Plex Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0',
        none: '0',
      },
      ringOffsetColor: {
        base: '#0a0c0e',
      },
      keyframes: {
        dash: {
          to: { strokeDashoffset: '-24' },
        },
      },
      animation: {
        dash: 'dash 1s linear infinite',
      },
    },
  },
  plugins: [],
}
