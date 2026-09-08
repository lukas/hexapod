#!/bin/sh
# Find (and optionally push) hexapod work that exists only on this machine.
#
# Two failure modes have actually lost work here, and this checks for both:
#
# 1. A clone with a NARROW remote.origin.fetch refspec never updates
#    origin/main. Every push then looks like a non-fast-forward, `git pull`
#    cannot help, and `git rebase origin/main` reports "up to date" against a
#    months-stale ref. A whole vision-service feature sat unpushed this way
#    while the session concluded "github is broken".
#
# 2. Worktrees live under /tmp, which macOS prunes. A commit that exists only
#    in a /tmp worktree is one cleanup away from gone.
#
# Reachability is checked against `git ls-remote` -- the actual remote -- not
# `git branch -r --contains`, which silently reports everything as unpushed in
# exactly the narrow-refspec clones that need checking most.
#
#   tools/git_unpushed_audit.sh            # report only
#   tools/git_unpushed_audit.sh --push     # also push anything unpushed
set -eu

PUSH=0
[ "${1:-}" = "--push" ] && PUSH=1

SUPPORT="$HOME/Library/Application Support/Hexapod Lab"
# Newline-separated on purpose: these paths contain spaces, so the list is
# read a line at a time rather than word-split by the shell.
CLONE_LIST="$HOME/hexapod
$HOME/Documents/ChatGPT/hexapod project
$SUPPORT/engineering-checkout-v1
$SUPPORT/engineering-checkout-v2
$SUPPORT/engineering-checkout-v3"

REMOTE_SHAS="$(mktemp)"
TOTALS="$(mktemp)"
printf '0 0\n' > "$TOTALS"
trap 'rm -f "$REMOTE_SHAS" "$TOTALS"' EXIT
got_remote=0
issues=0
unpushed=0

printf '%s\n' "$CLONE_LIST" | while IFS= read -r clone; do
  [ -n "$clone" ] || continue
  [ -d "$clone/.git" ] || continue   # worktrees have a .git FILE; skip them

  name="$(basename "$clone")"

  # Repair 1: guarantee main is fetchable, without widening a deliberately
  # narrow refspec into "fetch every orchestrator branch".
  if ! git -C "$clone" config --get-all remote.origin.fetch 2>/dev/null \
      | grep -qE 'refs/heads/(\*|main):'; then
    echo "[$name] remote.origin.fetch cannot see main -- adding it"
    git -C "$clone" config --add remote.origin.fetch \
      '+refs/heads/main:refs/remotes/origin/main'
    issues=$((issues + 1))
  fi
  git -C "$clone" fetch origin -q 2>/dev/null || true

  if [ "$got_remote" = "0" ]; then
    git -C "$clone" ls-remote origin > "$REMOTE_SHAS" 2>/dev/null && got_remote=1
  fi
  [ "$got_remote" = "1" ] || { echo "[$name] cannot reach the remote; skipping"; continue; }

  for wt in $(git -C "$clone" worktree list --porcelain | awk '/^worktree /{print $2}'); do
    head="$(git -C "$wt" rev-parse HEAD 2>/dev/null || true)"
    [ -n "$head" ] || continue
    grep -q "^$head" "$REMOTE_SHAS" && continue

    ahead="$(git -C "$wt" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
    [ "$ahead" = "0" ] && continue

    branch="$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    case "$branch" in
      HEAD) target="salvage/$(basename "$wt")" ;;   # detached: invent a name
      *)    target="$branch" ;;
    esac
    unpushed=$((unpushed + 1))
    echo "[$name] UNPUSHED $(basename "$wt") [$branch] +$ahead commit(s)"
    if [ "$PUSH" = "1" ]; then
      if git -C "$clone" push origin "${head}:refs/heads/${target}" >/dev/null 2>&1; then
        echo "          pushed -> $target"
      else
        echo "          PUSH FAILED -> $target"
      fi
    fi
  done
  echo "$issues $unpushed" > "$TOTALS"
done

read -r issues unpushed < "$TOTALS" 2>/dev/null || { issues=0; unpushed=0; }
echo
echo "refspec repairs: $issues | unpushed worktrees: $unpushed"
if [ "$PUSH" = "0" ] && [ "$unpushed" != "0" ]; then
  echo "re-run with --push to preserve them"
fi
exit 0
