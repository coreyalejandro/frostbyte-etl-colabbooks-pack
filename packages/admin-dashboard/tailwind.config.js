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
        interactive: '#2c3035',
        border: '#3c4045',
        inactive: '#5f6368',
        'text-secondary': '#9aa0a6',
        'text-primary': '#e8eaed',
        accent: '#eab308',
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
    },
  },
  plugins: [],
}
