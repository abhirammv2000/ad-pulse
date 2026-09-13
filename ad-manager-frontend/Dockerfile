# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

# `npm ci` installs exactly the lockfile, and the previous `--force` was masking
# peer-dependency conflicts rather than resolving them.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Run stage — nginx serving the static build. The old image shipped the Create
# React App dev server, which is why the deployment asked for 4Gi and 3 CPUs.
FROM nginx:1.27-alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/99-adpulse-config.sh
RUN chmod +x /docker-entrypoint.d/99-adpulse-config.sh

EXPOSE 3000
