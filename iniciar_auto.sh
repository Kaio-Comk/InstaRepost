#!/usr/bin/env bash
# =========================================================
#  InstaRepost — modo 24/7 totalmente automático.
#  Sobe: painel (serve /media) + túnel Cloudflare + scheduler.
#  Resolve a URL do túnel automaticamente (ela muda a cada reinício)
#  e injeta em PUBLIC_MEDIA_BASE_URL antes de subir o scheduler.
#
#  Posta 1 vídeo por hora (POLL_INTERVAL_SECONDS no .env), sem repetir.
#  Cole os links dos Reels em data/queue.txt (1 por linha).
# =========================================================
set -u
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"  # systemd usa PATH mínimo
cd "$(dirname "$(readlink -f "$0")")" || exit 1   # roda de onde o projeto estiver

PORT=8021
PY="./venv/bin/python"
mkdir -p logs

cleanup() {
  echo "Encerrando…"
  [ -n "${PANEL_PID:-}" ] && kill "$PANEL_PID" 2>/dev/null
  [ -n "${CF_PID:-}" ] && kill "$CF_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# 1) Painel (serve o vídeo em /media para a Meta baixar)
WEB_PORT=$PORT $PY cli.py web > logs/panel.log 2>&1 &
PANEL_PID=$!
echo "Painel iniciado (PID $PANEL_PID) em http://127.0.0.1:$PORT"

# 2) Túnel Cloudflare
: > logs/cloudflared.log
cloudflared tunnel --url "http://localhost:$PORT" > logs/cloudflared.log 2>&1 &
CF_PID=$!

# 3) Aguarda a URL pública aparecer no log
echo "Aguardando URL do túnel…"
TUNNEL=""
for _ in $(seq 1 40); do
  TUNNEL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" logs/cloudflared.log | head -1)
  [ -n "$TUNNEL" ] && break
  sleep 2
done
if [ -z "$TUNNEL" ]; then
  echo "ERRO: não consegui obter a URL do túnel. Veja logs/cloudflared.log"
  exit 1
fi
export PUBLIC_MEDIA_BASE_URL="$TUNNEL/media"
echo "Túnel pronto: $PUBLIC_MEDIA_BASE_URL"

# 4) Scheduler em primeiro plano (posta 1/hora). Ctrl+C encerra tudo.
echo "Scheduler 24/7 rodando. Cole links em data/queue.txt. Ctrl+C para parar."
$PY cli.py scheduler
