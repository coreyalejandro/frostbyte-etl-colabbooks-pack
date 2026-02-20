# Frostbyte Admin Dashboard
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build for production (base: / so app is served at root)
RUN npm run build

# Copy custom server (redirects /admin -> /, serves dist, no-cache for index.html)
COPY server.js ./

# Expose port
EXPOSE 5174

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5174/ || exit 1

# Custom server: /admin -> / redirect, SPA at root
CMD ["node", "server.js"]
