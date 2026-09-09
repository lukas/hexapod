#!/bin/sh
# Render the TRACKED proxy templates, then apply them to the relay/BuildViz.
# Run --prepare-only to validate/render without changing running services.
# Inputs: ~/.hexapod/web-login.hash; the controller owns the SSO signing key.
set -eu
umask 077
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO="$(CDPATH= cd -- "$HERE/../.." && pwd)"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/coreweave.yaml}"
D="${HEXAPOD_SSO_CONFIG_DIR:-$HOME/.hexapod/caddy-sso}"
HASH_PATH="${HEXAPOD_SSO_HASH_FILE:-$HOME/.hexapod/web-login.hash}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/hexapod-sso.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
case "${1:-}" in
    ""|--prepare-only) ;;
    *) echo "usage: $0 [--prepare-only]" >&2; exit 2 ;;
esac

# The rendered files contain the local password hash, never a repo secret.
# Regenerate on EVERY invocation so old local copies cannot undo auth fixes.
uv run --frozen --project "$REPO" python - "$HERE" "$HASH_PATH" "$TMP" <<'PY'
from pathlib import Path
import sys
source, hash_path, output = map(Path, sys.argv[1:])
password_hash = hash_path.read_text().strip()
if not password_hash.startswith(("$2a$", "$2b$", "$2y$")):
    raise SystemExit("web-login.hash must contain a bcrypt password hash")
for name in ("camera-relay.Caddyfile", "buildviz.Caddyfile"):
    text = (source / name).read_text().replace("{env.LAB_LOGIN_HASH}", password_hash)
    (output / name).write_text(text)
PY
if command -v caddy >/dev/null 2>&1; then
    caddy adapt --config "$TMP/camera-relay.Caddyfile" --adapter caddyfile >/dev/null
    caddy adapt --config "$TMP/buildviz.Caddyfile" --adapter caddyfile >/dev/null
fi
mkdir -p "$D"
install -m 600 "$TMP/camera-relay.Caddyfile" "$D/camera-relay.Caddyfile"
install -m 600 "$TMP/buildviz.Caddyfile" "$D/buildviz.Caddyfile"
if [ "${1:-}" = --prepare-only ]; then
    echo "Rendered tracked SSO templates in $D; running services unchanged."
    exit 0
fi

# Lab verifies signed cookies itself, rather than trusting forwarded headers.
# Keep the shared key private and replace it only after a successful read.
CONTROLLER="${HEXAPOD_CONTROLLER_POD:-hexapod-sweep-friction}"
kubectl exec "$CONTROLLER" -- cat /workspace/.sso_secret > "$TMP/sso-secret"
if [ ! -s "$TMP/sso-secret" ]; then
    echo "Controller returned an empty SSO signing key" >&2
    exit 1
fi
install -m 600 "$TMP/sso-secret" "$HOME/.hexapod/sso-secret"

echo ">> camera-relay (Secret camera-relay-caddy)"
kubectl create secret generic camera-relay-caddy --from-file=Caddyfile="$D/camera-relay.Caddyfile" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/camera-relay
kubectl rollout status deployment/camera-relay --timeout=180s

echo ">> buildviz (ConfigMap for future restarts + live reload; subPath mounts never refresh)"
uv run --frozen --project "$REPO" python - "$D/buildviz.Caddyfile" <<'PY' > "$TMP/buildviz-patch.json"
import json, sys
from pathlib import Path
print(json.dumps({"data": {"Caddyfile": Path(sys.argv[1]).read_text()}}))
PY
kubectl patch configmap buildviz-bootstrap --type merge --patch-file "$TMP/buildviz-patch.json"
kubectl exec -i buildviz-hub -c caddy -- sh -c \
  'cat > /tmp/Caddyfile.new && caddy validate --config /tmp/Caddyfile.new && caddy reload --config /tmp/Caddyfile.new' \
  < "$D/buildviz.Caddyfile"

echo ">> verify: unauthenticated browser GETs should redirect; agent paths retain their own gates"
for u in camera.cwd1f0-new-cluster.coreweave.app/ robot-lab.cwd1f0-new-cluster.coreweave.app/ \
         robot-lab.cwd1f0-new-cluster.coreweave.app/healthz buildviz.cwd1f0-new-cluster.coreweave.app/ \
         buildviz.cwd1f0-new-cluster.coreweave.app/__buildviz/status; do
  printf "  %-58s -> %s\n" "$u" "$(curl -s -m 12 -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Accept: text/html' "https://$u")"
done
echo "Restart Robot Lab with the updated run-hexapod-lab.sh launcher to enable local SSO verification."
