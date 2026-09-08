#!/usr/bin/env bash
# Unified script runner for the repo:
#   1. Keeps the single repo-root `.venv` in sync with `uv.lock` (uv sync is a
#      fast no-op when nothing changed), so every project shares one set of
#      installed wheels. Dependencies are declared in pyproject.toml.
#   2. Resolves the target script either as an absolute path, a path relative
#      to the repo root (e.g. `hexapod_walker/prototype_sts3215/build_all.py`),
#      or a bare script name (which is searched for under the repo).
#   3. cds into the script's own directory before running it, so relative
#      paths used by the script (writing STLs, reading helper files) resolve
#      next to the script. The prototype packages are importable from any cwd
#      via the editable install (see [tool.hatch.build.targets.wheel] in
#      pyproject.toml); PYTHONPATH is still extended with the repo root for the
#      archived generations that import repo-root-relative modules.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required for Python commands in this repo; install uv first." >&2
    exit 127
fi

# Create/update .venv from uv.lock. `--frozen` never rewrites the lock here;
# change dependencies in pyproject.toml and run `uv lock` explicitly.
uv sync --frozen --quiet

if [ "$#" -eq 0 ]; then
    echo "usage: ./run.sh <script.py> [args...]" >&2
    exit 2
fi
TARGET="$1"
shift

# Resolve target.
if [ -f "$TARGET" ]; then
    TARGET_ABS="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"
elif [ -f "$ROOT_DIR/$TARGET" ]; then
    TARGET_ABS="$ROOT_DIR/$TARGET"
else
    # bare name → search under the repo (skip .venv etc.)
    HIT="$(find "$ROOT_DIR" -name "$(basename "$TARGET")" -type f \
                  -not -path "*/.venv/*" -not -path "*/.git/*" \
                  -not -path "*/node_modules/*" \
                  -not -path "*/__pycache__/*" 2>/dev/null | head -1)"
    if [ -z "$HIT" ]; then
        echo "Could not find script: $TARGET" >&2
        exit 1
    fi
    TARGET_ABS="$HIT"
fi

TARGET_DIR="$(dirname "$TARGET_ABS")"
TARGET_NAME="$(basename "$TARGET_ABS")"
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$TARGET_DIR"
# Display path relative to repo root for nicer logs.
REL_DISPLAY="${TARGET_ABS#$ROOT_DIR/}"
echo "Running $REL_DISPLAY $*..."
# --project pins the repo-root env even though we cd'd into the script dir.
uv run --frozen --project "$ROOT_DIR" python "$TARGET_NAME" "$@"
