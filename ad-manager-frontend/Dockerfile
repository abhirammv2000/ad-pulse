# Build stage
FROM node:24.21.0-alpine3.24 AS builder
WORKDIR /app

# `npm ci` installs exactly the lockfile.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Run stage: nginx serving the static build. The old image shipped the Create
# React App dev server, which is why the deployment asked for 4Gi and 3 CPUs.
FROM nginx:1.30-alpine3.24
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/99-adpulse-config.sh
RUN chmod +x /docker-entrypoint.d/99-adpulse-config.sh

EXPOSE 3000
