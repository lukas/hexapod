#!/bin/sh
# Send a hand-run experiment (any robot, any device) to Robot Lab v2.
#
#   HEXAPOD_LAB_TOKEN=... lab2-send.sh [-r hexapod2] [-s ok|failed] \
#       -t "title" -w "why" [-f "what we found"] [folder-or-files...]
#
# Creates the run, then uploads each file with one PUT. Only needs curl.
set -eu
BASE="${HEXAPOD_LAB_URL:-https://robot-lab.cwd1f0-new-cluster.coreweave.app}"
: "${HEXAPOD_LAB_TOKEN:?set HEXAPOD_LAB_TOKEN to the operator bearer token}"
robot=hexapod2 status=ok title= why= found=
while getopts "r:s:t:w:f:" opt; do
  case $opt in r) robot=$OPTARG;; s) status=$OPTARG;; t) title=$OPTARG;; w) why=$OPTARG;; f) found=$OPTARG;; *) exit 2;; esac
done
shift $((OPTIND - 1))
[ -n "$title" ] && [ -n "$why" ] || { echo "need -t title and -w why" >&2; exit 2; }
json=$(python3 -c 'import json,sys; print(json.dumps(dict(zip(["title","why","found","robot","status"], sys.argv[1:]))))' "$title" "$why" "$found" "$robot" "$status")
resp=$(curl -sS --fail -H "Authorization: Bearer $HEXAPOD_LAB_TOKEN" -H "Content-Type: application/json" -d "$json" "$BASE/v2/api/import")
rid=$(printf %s "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
echo "run $rid created"
upload() {
  name=$(basename "$1")
  curl -sS --fail -o /dev/null -H "Authorization: Bearer $HEXAPOD_LAB_TOKEN" -X PUT --data-binary @"$1" \
    "$BASE/v2/api/runs/$rid/files/$name" && echo "  uploaded $name"
}
for arg in "$@"; do
  if [ -d "$arg" ]; then
    for f in "$arg"/*; do [ -f "$f" ] && upload "$f"; done
  elif [ -f "$arg" ]; then
    upload "$arg"
  fi
done
echo "$BASE/v2/?robot=$robot"
