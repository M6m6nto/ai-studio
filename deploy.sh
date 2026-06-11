#!/usr/bin/env bash
# Deploy all studio sites (root + botgen + aitargetolog + pairbridge) to a VPS.
# Usage:  DOMAIN=yourdomain.com SERVER=root@178.105.220.38 bash deploy.sh
set -euo pipefail

DOMAIN="${DOMAIN:?Usage: DOMAIN=yourdomain.com SERVER=user@host bash deploy.sh}"
SERVER="${SERVER:?Usage: DOMAIN=yourdomain.com SERVER=user@host bash deploy.sh}"
EMAIL="${EMAIL:-vladislav.poddubotski@gmail.com}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uploading sites to $SERVER ..."
rsync -az --delete \
  --exclude '.git' --exclude 'deploy.sh' --exclude 'CNAME' \
  "$LOCAL_DIR"/ "$SERVER:/tmp/sites-upload/"

echo "==> Configuring server ..."
ssh "$SERVER" "DOMAIN='$DOMAIN' EMAIL='$EMAIL' bash -s" <<'REMOTE'
set -euo pipefail

run() { if [ "$(id -u)" = 0 ]; then "$@"; else sudo "$@"; fi; }
export DEBIAN_FRONTEND=noninteractive

# --- safety check: if port 80 is held by something other than nginx, stop ---
HOLDER="$(run ss -ltnp 2>/dev/null | awk '$4 ~ /:80$/ {print $NF}' | head -1 || true)"
if [ -n "$HOLDER" ] && ! echo "$HOLDER" | grep -qi nginx; then
  echo "!! Port 80 is used by: $HOLDER (not nginx)."
  echo "!! Aborting so nothing breaks. Tell me what runs there and we'll adapt."
  exit 1
fi

# --- install nginx + certbot if missing ---
command -v nginx   >/dev/null || { run apt-get update -qq; run apt-get install -y -qq nginx; }
command -v certbot >/dev/null || { run apt-get update -qq; run apt-get install -y -qq certbot python3-certbot-nginx; }

# --- place files ---
run mkdir -p "/var/www/$DOMAIN"
run rsync -a --delete /tmp/sites-upload/ "/var/www/$DOMAIN/"
rm -rf /tmp/sites-upload

# --- warn about other configs already claiming this domain ---
CONFLICTS="$(grep -rls "server_name.*$DOMAIN" /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "sites-enabled/$DOMAIN" || true)"
[ -n "$CONFLICTS" ] && echo "!! Note: other nginx configs also mention $DOMAIN: $CONFLICTS"

# --- nginx server block ---
run tee "/etc/nginx/sites-available/$DOMAIN" >/dev/null <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;
    root /var/www/$DOMAIN;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    gzip on;
    gzip_types text/html text/css application/javascript;
    add_header X-Content-Type-Options nosniff;
}
NGINX
run ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
run nginx -t
run systemctl reload nginx
echo "==> HTTP is up."

# --- HTTPS via Let's Encrypt (www included if its DNS exists, else apex only) ---
if certbot certificates 2>/dev/null | grep -q "Domains:.*$DOMAIN"; then
  echo "==> Certificate already exists, skipping issue."
  run certbot install --nginx -d "$DOMAIN" --non-interactive || true
else
  run certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
      --non-interactive --agree-tos -m "$EMAIL" --redirect \
  || run certbot --nginx -d "$DOMAIN" \
      --non-interactive --agree-tos -m "$EMAIL" --redirect
fi

echo "==> Done. Live at: https://$DOMAIN"
REMOTE

echo ""
echo "==> Deployed:"
echo "    https://$DOMAIN/              (studio)"
echo "    https://$DOMAIN/botgen/       (BotGEN)"
echo "    https://$DOMAIN/aitargetolog/ (AI Targetolog)"
echo "    https://$DOMAIN/pairbridge/   (PairBridge)"
