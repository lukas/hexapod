#!/bin/sh
set -eu

LAB_TOKEN="$(/usr/bin/security find-generic-password -a assistants -s 'Hexapod Lab API' -w)"
/bin/launchctl setenv HEXAPOD_LAB_TOKEN "$LAB_TOKEN"
