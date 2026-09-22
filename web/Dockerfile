# syntax=docker/dockerfile:1

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Variables de build para Vite (opcionales si se inyectan en runtime)
ARG VITE_API_BASE_URL=/
ARG VITE_FORCE_MOCKS=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_FORCE_MOCKS=$VITE_FORCE_MOCKS
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY docker/nginx.conf /etc/nginx/templates/default.conf.template
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --from=build /app/dist /usr/share/nginx/html

ENV PORT=80
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD sh -c 'wget -qO- http://127.0.0.1:${PORT:-80}/nginx-health || exit 1'

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
