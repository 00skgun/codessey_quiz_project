#!/usr/bin/env bash
set -euo pipefail
umask 0007
[[ $EUID -ne 0 && $(id -un) == agent-admin ]] || {
    echo 'Run as agent-admin: sudo -u agent-admin -H /home/agent-admin/agent-app/bin/run-app.sh' >&2; exit 1;
}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/../agent-env.sh"
cd -- "$AGENT_HOME"
[[ -f $AGENT_APP_PATH ]] || { echo "Missing provided app: $AGENT_APP_PATH" >&2; exit 1; }
case $AGENT_APP_PATH in
    *.py) exec /usr/bin/python3 -u "$AGENT_APP_PATH" ;;
    *)
        # The supplied binary disagrees with the PDF: it expects the key DIRECTORY.
        # Keep agent-env.sh at the PDF value and adapt only the binary process.
        if [[ -f $AGENT_KEY_PATH ]]; then
            export AGENT_KEY_PATH
            AGENT_KEY_PATH=$(dirname -- "$AGENT_KEY_PATH")
            printf '[INFO] Provided binary compatibility: AGENT_KEY_PATH=%s (directory)\n' "$AGENT_KEY_PATH"
        fi
        exec "$AGENT_APP_PATH"
        ;;
esac
