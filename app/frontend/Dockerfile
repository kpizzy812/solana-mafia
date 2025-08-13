# Use Node.js LTS Alpine image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies for node-gyp, usb package, and curl for healthcheck
RUN apk add --no-cache python3 make g++ curl linux-headers eudev-dev libusb-dev

# Copy package files
COPY package*.json ./

# Install dependencies with flags to skip problematic packages
RUN npm ci --legacy-peer-deps --no-optional

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Default command (can be overridden in docker-compose)
CMD ["npm", "run", "dev"]