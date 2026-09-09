#!/bin/sh
# Switch the camera/robot-lab relay and the BuildViz proxy to the shared
# sign-in (forward_auth to hexapod.cwd1f0.../auth). Cluster Secret/ConfigMap
# writes are denied to the assistant session, so an operator runs it by hand.
# Inputs: ~/.hexapod/caddy-sso/*.Caddyfile (real hashes) and ~/.hexapod/web-login.
set -eu
export KUBECONFIG="$HOME/.kube/coreweave.yaml"
D="$HOME/.hexapod/caddy-sso"

echo ">> camera-relay (Secret camera-relay-caddy)"
kubectl create secret generic camera-relay-caddy --from-file=Caddyfile="$D/camera-relay.Caddyfile" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/camera-relay
kubectl rollout status deployment/camera-relay --timeout=180s

echo ">> buildviz (ConfigMap for future restarts + live reload now; the mount is a subPath and never refreshes)"
python3 - "$D/buildviz.Caddyfile" <<'PY' > /tmp/bv_patch.json
import json, sys; print(json.dumps({"data": {"Caddyfile": open(sys.argv[1]).read()}}))
PY
kubectl patch configmap buildviz-bootstrap --type merge --patch-file /tmp/bv_patch.json; rm -f /tmp/bv_patch.json
kubectl exec -i buildviz-hub -c caddy -- sh -c \
  'cat > /tmp/Caddyfile.new && caddy validate --config /tmp/Caddyfile.new && caddy reload --config /tmp/Caddyfile.new' \
  < "$D/buildviz.Caddyfile"

echo ">> verify: browser GETs without a cookie should 302 to the sign-in form; agent paths should not"
sleep 8
for u in camera.cwd1f0-new-cluster.coreweave.app/ robot-lab.cwd1f0-new-cluster.coreweave.app/ \
         robot-lab.cwd1f0-new-cluster.coreweave.app/healthz buildviz.cwd1f0-new-cluster.coreweave.app/ \
         buildviz.cwd1f0-new-cluster.coreweave.app/__buildviz/status; do
  printf "  %-58s -> %s\n" "$u" "$(curl -s -m 12 -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Accept: text/html' "https://$u")"
done
echo "done. Sign in at https://hexapod.cwd1f0-new-cluster.coreweave.app/login  (user: $(sed -n 1p "$HOME/.hexapod/web-login"))"
