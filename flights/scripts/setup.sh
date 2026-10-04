#!/usr/bin/env bash
# One-shot environment setup for the flight-hunt toolkit in a fresh (cloud) container.
# Idempotent: safe to re-run. Usage:  bash flights/scripts/setup.sh
set -u
cd "$(dirname "$0")"

echo "== Python deps"
for f in requirements.txt requirements-ota.txt; do
  [ -f "$f" ] && pip install -q -r "$f" 2>&1 | tail -2
done

echo "== Playwright / Chromium"
# The container ships Chromium build 1194 in /opt/pw-browsers, which matches Playwright 1.56.
# NEVER run `playwright install` here (it downloads browsers and isn't needed).
python3 -c "import playwright" 2>/dev/null || pip install -q playwright==1.56.0

# Chromium uses its own NSS trust store, which starts empty in some containers. Without the
# agent-proxy CA every page fails with ERR_CERT_AUTHORITY_INVALID. This ADDS the proxy CA as
# trusted (verification stays on). See /root/.ccr/README.md.
CA=/root/.ccr/agent-proxy-ca.crt
if [ -f "$CA" ]; then
  command -v certutil >/dev/null || (apt-get install -y -q libnss3-tools >/dev/null 2>&1 || echo "  ! could not install libnss3-tools")
  mkdir -p "$HOME/.pki/nssdb"
  [ -f "$HOME/.pki/nssdb/cert9.db" ] || certutil -N -d "sql:$HOME/.pki/nssdb" --empty-password
  if certutil -L -d "sql:$HOME/.pki/nssdb" 2>/dev/null | grep -q ccr-agent-proxy; then
    echo "  proxy CA already trusted by Chromium"
  else
    certutil -A -d "sql:$HOME/.pki/nssdb" -n ccr-agent-proxy -t "C,," -i "$CA" && echo "  proxy CA added to Chromium NSS store"
  fi
else
  echo "  (no agent proxy CA found, so not in the managed cloud env; skipping NSS step)"
fi

echo "== Smoke tests"
python3 fx.py 100 USD || echo "  ! fx failed"
python3 - <<'EOF'
import json, urllib.request
for name, url in (("kiwi-mcp", "https://mcp.kiwi.com"), ("skiplagged-mcp", "https://mcp.skiplagged.com/mcp")):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  {name}: HTTP {r.status} ok")
    except Exception as e:
        print(f"  ! {name}: {e}")
EOF
echo "== done"
