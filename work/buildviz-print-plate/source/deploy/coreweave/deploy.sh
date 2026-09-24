#!/bin/sh
# Deploy (or redeploy) the BuildViz hub to the CoreWeave cluster.
#
#   deploy/coreweave/deploy.sh
#
# Applies buildviz.yaml and ships the local working tree into the pod as a
# tarball (the repo is private, so no in-cluster git clone). The pod's
# bootstrap loop notices the new tarball and restarts the hub in place, so
# routine redeploys do NOT delete the pod (preserving the Let's Encrypt cert
# in the caddy sidecar). If the pod spec itself changed, kubectl apply fails
# on the immutable pod and we fall back to delete + recreate.
set -eu

KUBECONFIG=${KUBECONFIG:-$HOME/.kube/coreweave.yaml}
export KUBECONFIG

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MANIFEST="$REPO_ROOT/deploy/coreweave/buildviz.yaml"
POD=buildviz-hub
NS=default

echo "==> Ensuring API key secret exists"
if ! kubectl -n "$NS" get secret buildviz-api-key >/dev/null 2>&1; then
  kubectl -n "$NS" create secret generic buildviz-api-key \
    --from-literal=key="$(openssl rand -hex 24)"
  echo "    generated new API key (stored in secret buildviz-api-key)"
fi

echo "==> Applying manifests"
if ! kubectl apply -f "$MANIFEST"; then
  echo "==> Pod spec changed (immutable); recreating pod (TLS cert will be re-issued)"
  kubectl -n "$NS" delete pod "$POD" --ignore-not-found --wait=true
  kubectl apply -f "$MANIFEST"
fi

echo "==> Waiting for pod to be running"
kubectl -n "$NS" wait --for=jsonpath='{.status.phase}'=Running "pod/$POD" --timeout=180s

echo "==> Packing source (working tree, minus node_modules/.git/dist)"
TARBALL=$(mktemp -t buildviz-src).tgz
tar -czf "$TARBALL" -C "$REPO_ROOT" \
  --exclude node_modules --exclude .git --exclude dist --exclude '*/plates' .

echo "==> Shipping source to the pod ($(du -h "$TARBALL" | cut -f1))"
kubectl -n "$NS" cp "$TARBALL" "$POD:/work/src.tgz.part" -c hub
kubectl -n "$NS" exec "$POD" -c hub -- mv /work/src.tgz.part /work/src.tgz
rm -f "$TARBALL"

echo "==> Waiting for the hub to answer (npm install runs in the pod; this can take a few minutes)"
sleep 15
for i in $(seq 1 90); do
  if kubectl -n "$NS" exec "$POD" -c hub -- \
    node -e 'fetch("http://127.0.0.1:5183/__buildviz/status").then(r=>r.json()).then(s=>{if(s.service!=="buildviz-hub")process.exit(1)}).catch(()=>process.exit(1))' \
    >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo "==> Hub status"
kubectl -n "$NS" exec "$POD" -c hub -- node -e 'fetch("http://127.0.0.1:5183/__buildviz/status").then(r=>r.json()).then(s=>console.log(JSON.stringify({service:s.service,version:s.version,builds:(s.projects||[]).flatMap(p=>p.builds||[]).length},null,2)))'

HOSTNAME=$(kubectl -n "$NS" get svc buildviz -o jsonpath='{.status.conditions[?(@.type=="ExternalRecords")].message}' 2>/dev/null || true)
EXTERNAL=$(kubectl -n "$NS" get svc buildviz -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
API_KEY=$(kubectl -n "$NS" get secret buildviz-api-key -o jsonpath='{.data.key}' | base64 -d)
echo ""
echo "BuildViz hub deployed."
[ -n "$HOSTNAME" ] && echo "  URL: https://$HOSTNAME/"
[ -n "$EXTERNAL" ] && echo "  IP:  http://$EXTERNAL/ (HTTP only; TLS cert is for the hostname)"
[ -n "$HOSTNAME" ] && echo "  MCP: https://$HOSTNAME/mcp (requires API key)"
echo "  API key: $API_KEY"
