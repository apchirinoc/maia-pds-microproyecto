#!/bin/sh
set -e

# Configurar el puerto de nginx si se especifica PORT dinámico (típico en Railway, Render, etc.)
export PORT="${PORT:-80}"

# Generar el archivo de configuración de variables de entorno en tiempo de ejecución
cat <<EOF > /usr/share/nginx/html/env-config.js
window.__ENV__ = {
  VITE_API_BASE_URL: "${VITE_API_BASE_URL:-${API_URL:-}}",
  VITE_FORCE_MOCKS: "${VITE_FORCE_MOCKS:-}",
  VITE_API_TIMEOUT_MS: "${VITE_API_TIMEOUT_MS:-}",
  VITE_HEALTH_TIMEOUT_MS: "${VITE_HEALTH_TIMEOUT_MS:-}",
  VITE_HEALTH_POLL_MS: "${VITE_HEALTH_POLL_MS:-}"
};
EOF

# Sustituir variables en la plantilla de configuración de Nginx si existe
if [ -f /etc/nginx/templates/default.conf.template ]; then
  envsubst '\$PORT' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
fi

exec "$@"
