import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

function cspPlugin(): Plugin {
  return {
    name: 'csp-meta',
    transformIndexHtml(html, ctx) {
      if (ctx.server) return html // skip in dev mode (HMR needs inline scripts)
      const csp = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
      ].join('; ')
      return html.replace(
        '</head>',
        `  <meta http-equiv="Content-Security-Policy" content="${csp}" />\n  </head>`,
      )
    },
  }
}

export default defineConfig({
  plugins: [react(), cspPlugin()],
  base: '/',
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
