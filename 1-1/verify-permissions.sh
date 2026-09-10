#!/usr/bin/env bash
# Real positive AND negative access checks; removes only its uniquely named probe files.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo on the practice Linux machine.' >&2; exit 1; }
app_home=/home/agent-admin/agent-app
probe=".permission-probe-$$-$RANDOM"
cleanup() {
    rm -f -- "$app_home/upload_files/$probe" "$app_home/api_keys/$probe" "/var/log/agent-app/$probe"
}
trap cleanup EXIT
for directory in "$app_home/upload_files" "$app_home/api_keys" /var/log/agent-app; do
    sudo -u agent-admin -- bash -c 'umask 077; printf "admin\n" > "$1"' bash "$directory/$probe"
    sudo -u agent-dev -- bash -c 'cat "$1" >/dev/null; printf "dev\n" >> "$1"' bash "$directory/$probe"
    echo "[OK] admin/dev read + write: $directory (default ACL inherits even with umask 077)"
done
sudo -u agent-test -- bash -c 'cat "$1" >/dev/null; printf "test\n" >> "$1"' bash "$app_home/upload_files/$probe"
echo '[OK] agent-test can read/write upload_files'
for directory in "$app_home/api_keys" /var/log/agent-app; do
    if sudo -u agent-test -- cat "$directory/$probe" >/dev/null 2>&1; then
        echo "[FAIL] agent-test read forbidden directory: $directory" >&2; exit 1;
    fi
    if sudo -u agent-test -- bash -c 'printf "bad\n" >> "$1"' bash "$directory/$probe" 2>/dev/null; then
        echo "[FAIL] agent-test wrote forbidden directory: $directory" >&2; exit 1;
    fi
    echo "[OK] agent-test denied read/write: $directory"
done
stat -c '%U %G %a %n' "$app_home/bin/monitor.sh"
[[ $(stat -c '%U:%G:%a' "$app_home/bin/monitor.sh") == agent-dev:agent-core:750 ]]
