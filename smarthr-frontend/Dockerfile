# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmmirror.com

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm config set registry ${NPM_REGISTRY} \
    && npm ci --no-audit --no-fund

# Copy source
COPY . .

# Build for production
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy build output from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
