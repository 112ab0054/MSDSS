#!/bin/sh
set -eu
expected=72beea139e644e9e1b6981b717d57dfa68ad3106
marker=/app/packages/.msdss-core-commit
if [ -f "$marker" ]; then
    [ "$(cat "$marker")" = "$expected" ] || { echo 'Core volume version mismatch' >&2; exit 1; }
    exit 0
fi
sha256sum -c .msdss-core.tar.sha256
tar -xf /app/.msdss-core.tar -C /app
printf '%s\n' "$expected" > "$marker"
echo 'Pinned Bagisto core copied into dedicated Linux volume'
