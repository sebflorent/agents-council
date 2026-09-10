#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer supports macOS launchd only." >&2
  exit 1
fi

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CONTEXT_DIR=${1:-""}
LABEL="com.agents-council.em-attention"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/.em-attention-os/logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

python3 - "$PLIST" "$REPO_DIR" "$CONTEXT_DIR" "$LOG_DIR" <<'PY'
import plistlib
import sys
from pathlib import Path

plist_path, repo_dir, context_dir, log_dir = sys.argv[1:]
environment = {"EM_ATTENTION_STATE_DIR": str(Path.home() / ".em-attention-os")}
if context_dir:
    environment["EM_ATTENTION_CONTEXT_DIR"] = str(Path(context_dir).expanduser().resolve())

payload = {
    "Label": "com.agents-council.em-attention",
    "ProgramArguments": [str(Path(repo_dir) / "scripts" / "em-attention-daily.sh")],
    "WorkingDirectory": repo_dir,
    "StartCalendarInterval": [
        {"Weekday": day, "Hour": 7, "Minute": 15} for day in range(2, 7)
    ],
    "EnvironmentVariables": environment,
    "StandardOutPath": str(Path(log_dir) / "daily.log"),
    "StandardErrorPath": str(Path(log_dir) / "daily-error.log"),
    "RunAtLoad": False,
}
with open(plist_path, "wb") as handle:
    plistlib.dump(payload, handle)
PY

chmod +x "$REPO_DIR/scripts/em-attention-daily.sh"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed weekday Attention OS brief at 07:15."
echo "LaunchAgent: $PLIST"
echo "Private reports: $HOME/.em-attention-os/daily/"
