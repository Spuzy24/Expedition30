#!/usr/bin/env bash
# One-shot environment setup for the flight-hunt toolkit in a fresh (cloud) container.
# Idempotent: safe to re-run. Exits non-zero if a required step failed. Usage:  bash flights/scripts/setup.sh
set -uo pipefail
cd "$(dirname "$0")"
FAIL=0
fail() { echo "  ! $*"; FAIL=1; }

echo "== Python deps"
# `python3 -m pip` installs for the interpreter the scripts actually run with (`pip` may belong to another one).
pip_install() {
  local out
  out=$(python3 -m pip install -q "$@" 2>&1) && { echo "$out" | grep -v "Running pip as the 'root' user" | tail -2; return 0; }
  if echo "$out" | grep -q "externally-managed-environment" && [ -d /root/.ccr ]; then
    # PEP 668 system Python in the disposable cloud container: allowed here, never on a workstation (use a venv)
    python3 -m pip install -q --break-system-packages "$@" 2>&1 | tail -2
    return "${PIPESTATUS[0]}"
  fi
  echo "$out" | tail -5
  return 1
}
for f in requirements.txt requirements-ota.txt; do
  [ -f "$f" ] || continue
  pip_install -r "$f" || fail "pip install -r $f failed (externally managed Python? use: python3 -m venv .venv)"
done

echo "== Playwright / Chromium"
# The container ships Chromium build 1194 in /opt/pw-browsers, which matches Playwright 1.56.
# NEVER run `playwright install` here (it downloads browsers and isn't needed).
python3 -c "import playwright" 2>/dev/null || pip_install playwright==1.56.0 || fail "playwright not installed"
if [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && [ -d /opt/pw-browsers ]; then
  export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
  echo "  PLAYWRIGHT_BROWSERS_PATH was unset; using /opt/pw-browsers (export it in your shell too)"
fi

# Chromium uses its own NSS trust store, which starts empty in some containers. Without the
# agent-proxy CA every page fails with ERR_CERT_AUTHORITY_INVALID. This ADDS the proxy CA as
# trusted (verification stays on). See /root/.ccr/README.md.
CA=/root/.ccr/agent-proxy-ca.crt
DB="sql:$HOME/.pki/nssdb"
if [ -f "$CA" ]; then
  if ! command -v certutil >/dev/null; then
    # fresh images have empty apt lists: install fails with "Unable to locate package" without an update
    (apt-get update -qq && apt-get install -y -q libnss3-tools) >/dev/null 2>&1
  fi
  if command -v certutil >/dev/null; then
    mkdir -p "$HOME/.pki/nssdb"
    [ -f "$HOME/.pki/nssdb/cert9.db" ] || certutil -N -d "$DB" --empty-password
    want=$(openssl x509 -in "$CA" -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2)
    have=$(certutil -L -d "$DB" -n ccr-agent-proxy -a 2>/dev/null | openssl x509 -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2)
    if [ -n "$have" ] && [ "$have" = "$want" ]; then
      echo "  proxy CA already trusted by Chromium"
    else
      # missing, or a stale CA under the same nickname (the proxy CA can change between containers)
      [ -n "$have" ] && certutil -D -d "$DB" -n ccr-agent-proxy
      certutil -A -d "$DB" -n ccr-agent-proxy -t "C,," -i "$CA" && echo "  proxy CA added to Chromium NSS store" \
        || fail "could not add the proxy CA to $DB"
    fi
  else
    fail "certutil unavailable (apt-get install libnss3-tools failed): browser scripts will hit ERR_CERT_AUTHORITY_INVALID"
  fi
else
  echo "  (no agent proxy CA found, so not in the managed cloud env; skipping NSS step)"
fi

echo "== Smoke tests"
python3 fx.py 100 USD || fail "fx failed"
python3 - <<'EOF' || FAIL=1
import json, sys, urllib.request
bad = 0
for name, url in (("kiwi-mcp", "https://mcp.kiwi.com"), ("skiplagged-mcp", "https://mcp.skiplagged.com/mcp")):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  {name}: HTTP {r.status} ok")
    except Exception as e:
        print(f"  ! {name}: {e}")
        bad = 1
sys.exit(bad)
EOF
# The step most likely to break in a fresh container: Chromium launch + TLS through the proxy.
timeout 90 python3 - <<'EOF' || fail "headless Chromium smoke test failed (see above)"
import sys
sys.path.insert(0, ".")
from _browser import browser_page
with browser_page() as (page, _):
    r = page.goto("https://www.example.com/", wait_until="domcontentloaded", timeout=45000)
    print(f"  chromium: HTTP {r.status if r else '?'} via {'proxy' if __import__('os').environ.get('HTTPS_PROXY') else 'direct'}")
EOF
if [ "$FAIL" -ne 0 ]; then echo "== done WITH ERRORS"; else echo "== done"; fi
exit "$FAIL"
