#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
[[ $(id -un) == agent-admin ]] || { echo 'Run this script as agent-admin.' >&2; exit 1; }
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/../agent-env.sh"
[[ $AGENT_HOME == /home/agent-admin/agent-app ]] || { echo 'Unexpected AGENT_HOME' >&2; exit 1; }
command -v logger >/dev/null
work_dir=$(mktemp -d)
trap 'rm -f -- "$work_dir/old" "$work_dir/new" "$work_dir/error"; rmdir -- "$work_dir"' EXIT
if ! crontab -l > "$work_dir/old" 2> "$work_dir/error"; then
    grep -q '^no crontab for ' "$work_dir/error" || { cat "$work_dir/error" >&2; exit 1; }
fi
# Preserve all unrelated cron jobs. This exact marker identifies our one job.
awk '!/# agent-app-monitor-managed$/' "$work_dir/old" > "$work_dir/new"
printf '%s\n' '* * * * * /bin/bash /home/agent-admin/agent-app/bin/monitor.sh 2>&1 | /usr/bin/logger -t agent-monitor # agent-app-monitor-managed' >> "$work_dir/new"
crontab "$work_dir/new"
crontab -l
