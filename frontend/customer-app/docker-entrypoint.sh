#!/bin/sh
# ================================================================================
# DOCKER ENTRYPOINT - Configure nginx with dynamic PORT for Cloud Run
# ================================================================================

set -e

# Default port if not set by Cloud Run
PORT=${PORT:-80}

echo "Starting nginx on port $PORT..."

# Replace listen port in nginx config
sed -i "s/listen 80;/listen $PORT;/g" /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g "daemon off;"
