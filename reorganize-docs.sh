#!/usr/bin/env bash
set -euo pipefail

mkdir -p docs/guides docs/reference

if [ -f docs/deployment.md ]; then
  mv docs/deployment.md docs/guides/deployment.md
fi

if [ -f docs/architecture.md ]; then
  mv docs/architecture.md docs/reference/architecture.md
fi

if [ -f docs/api.md ]; then
  mv docs/api.md docs/reference/api.md
fi

if [ -f docs/development.md ]; then
  rm docs/development.md
fi
