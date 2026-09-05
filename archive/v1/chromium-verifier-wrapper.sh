#!/bin/sh
set -eu

: "${REAL_CHROMIUM:?REAL_CHROMIUM must point to a Chromium-compatible executable}"
exec "$REAL_CHROMIUM" --hide-scrollbars "$@"

