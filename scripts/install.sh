#!/usr/bin/env bash
# Install mob from its latest GitHub release.
#
# Usage:
#   ./scripts/install.sh            # install latest tagged release
#   ./scripts/install.sh v0.2.0     # install a specific tag
#
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/bboynton97/mob/main/scripts/install.sh | bash

set -euo pipefail

REPO="bboynton97/mob"
TAG="${1:-}"

if [ -z "${TAG}" ]; then
    echo "→ Looking up latest release of ${REPO}…"
    TAG=$(
        curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name":' \
        | sed -E 's/.*"tag_name":[[:space:]]*"([^"]+)".*/\1/' \
        | head -n 1
    )
fi

if [ -z "${TAG}" ]; then
    echo "✖ No tagged release found for ${REPO}." >&2
    echo "  Publish a release on GitHub first, or pass a tag as an argument." >&2
    exit 1
fi

SOURCE="git+https://github.com/${REPO}@${TAG}#subdirectory=client"
echo "→ Installing mob ${TAG}"

if command -v uv >/dev/null 2>&1; then
    uv tool install --force "${SOURCE}"
elif command -v pipx >/dev/null 2>&1; then
    pipx install --force "${SOURCE}"
else
    echo "✖ Need either 'uv' or 'pipx' on PATH to install." >&2
    echo "    uv  (recommended): https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "    pipx:              https://pipx.pypa.io/stable/installation/" >&2
    exit 1
fi

cat <<'EOF'

✓ Done. Try one of:
    mob frog
    mob cat
    mob dog
    mob turtle
    mob slime
EOF
