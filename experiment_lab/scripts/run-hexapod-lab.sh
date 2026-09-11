#!/bin/sh
# Launcher for the Robot Lab web service (com.lbiewald.hexapod-lab): the v2
# dashboard, JSON API, artifacts and /mcp on 127.0.0.1:8767, fronted by the
# Caddy tunnel at https://robot-lab.cwd1f0-new-cluster.coreweave.app. The
# loop itself is the separate com.lbiewald.hexapod-lab2 service (run-lab2.sh).
set -eu
umask 077

export PATH="/opt/homebrew/bin:/usr/local/bin:/Users/lukas/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

LAB_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Lab API' -w)"
ASSISTANTS_TOKEN="$(/usr/bin/security find-generic-password -a assistants -s 'Hexapod Lab API' -w)"
MOBILE_TOKEN="$(/usr/bin/security find-generic-password -a viewer -s 'Hexapod Research Mobile' -w)"
export HEXAPOD_API_KEYS="operator:operator:${LAB_TOKEN},operator:assistants:${ASSISTANTS_TOKEN},viewer:iphone:${MOBILE_TOKEN}"
unset LAB_TOKEN ASSISTANTS_TOKEN MOBILE_TOKEN
# The public site is fronted by Caddy with the one shared lab login. Caddy
# forwards that Basic header unchanged, and the Lab accepts
# Basic <name>:<token>, so registering the same credential as an operator key
# makes it sign in here too -- no second form. ~/.hexapod/web-login holds
# "user" then "password" on two lines, mode 0600.
WEB_LOGIN_FILE="/Users/lukas/.hexapod/web-login"
if [ -s "$WEB_LOGIN_FILE" ]; then
  WEB_LOGIN_USER="$(sed -n 1p "$WEB_LOGIN_FILE")"
  WEB_LOGIN_PASS="$(sed -n 2p "$WEB_LOGIN_FILE")"
  if [ -n "$WEB_LOGIN_USER" ] && [ -n "$WEB_LOGIN_PASS" ]; then
    HEXAPOD_API_KEYS="${HEXAPOD_API_KEYS},operator:${WEB_LOGIN_USER}:${WEB_LOGIN_PASS}"
  fi
  unset WEB_LOGIN_USER WEB_LOGIN_PASS
fi
export HEXAPOD_API_KEYS

# Browser single sign-on: verify the controller-signed hexapod_sso cookie
# directly (see hexapod_lab2/sso.py). Same secret as the controller pod.
SSO_SECRET_FILE="${HEXAPOD_SSO_SECRET_FILE:-/Users/lukas/.hexapod/sso-secret}"
if [ -s "$SSO_SECRET_FILE" ]; then
  export HEXAPOD_SSO_SECRET_FILE="$SSO_SECRET_FILE"
  export HEXAPOD_SSO_USERS="${HEXAPOD_SSO_USERS:-operator:lukas}"
  export HEXAPOD_SSO_COOKIE_DOMAIN="${HEXAPOD_SSO_COOKIE_DOMAIN:-.cwd1f0-new-cluster.coreweave.app}"
fi
unset SSO_SECRET_FILE

export HEXAPOD_BIND="127.0.0.1"
export HEXAPOD_PORT="8767"
export HEXAPOD_PUBLIC_BASE_URL="https://robot-lab.cwd1f0-new-cluster.coreweave.app"
# Same data as the loop: ~/Library/Application Support/Hexapod Lab/v2 (default).
exec "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-lab"
