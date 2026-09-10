#!/bin/sh
set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
STATE_DIR=${EM_ATTENTION_STATE_DIR:-"$HOME/.em-attention-os"}
CONTEXT_DIR=${EM_ATTENTION_CONTEXT_DIR:-""}
CALENDAR_JSON=${EM_ATTENTION_CALENDAR_JSON:-""}
TODAY=$(date +%F)

mkdir -p "$STATE_DIR/daily"

set -- python3 -m attention_os daily \
  --output "$STATE_DIR/daily/$TODAY.md" \
  --json-output "$STATE_DIR/daily/$TODAY.json"

if [ -n "$CONTEXT_DIR" ]; then
  set -- "$@" --context-dir "$CONTEXT_DIR"
fi
if [ -n "$CALENDAR_JSON" ] && [ -f "$CALENDAR_JSON" ]; then
  set -- "$@" --calendar-json "$CALENDAR_JSON"
fi

cd "$REPO_DIR"
"$@"
