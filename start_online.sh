#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🎱 Starting Rion Snooker Management Server..."
pkill -9 -f "server.py" 2>/dev/null || true
./venv/bin/python server.py > /tmp/transaction_web.log 2>&1 &

echo "🔒 Starting Secure Online Cloudflare Tunnel..."
pkill -9 -f "cloudflared tunnel" 2>/dev/null || true
./cloudflared tunnel --url http://127.0.0.1:8000 > /tmp/cloudflared.log 2>&1 &

sleep 4

ONLINE_URL=$(grep -o 'https://[-a-zA-Z0-9@:%._\+~#=]\+\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1)

echo "=============================================================================="
echo "✅ RION SNOOKER LOUNGE IS NOW LIVE & ONLINE!"
echo "🌐 Global Public URL (Phone/Laptop/Anywhere): $ONLINE_URL"
echo "📶 Local Wi-Fi URL (Inside Club): http://$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '192.168.0.123'):8000"
echo "💻 Mac Local URL: http://localhost:8000"
echo "=============================================================================="
