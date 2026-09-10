#!/usr/bin/env bash
# Read actual system state. Output includes failures; it does not declare the mission complete.
set -uo pipefail
export LC_ALL=C
[[ $EUID -eq 0 ]] || { echo 'Run with sudo on the practice Linux machine.' >&2; exit 1; }
section() { printf '\n===== %s =====\n' "$*"; }
run() {
    printf '\n$'; printf ' %q' "$@"; printf '\n'
    "$@"
    local result=$?
    printf '[exit status: %s]\n' "$result"
}
section 'Capture time and environment'
run date --iso-8601=seconds
run cat /etc/os-release
run uname -a
section 'Effective SSH configuration and listening sockets'
run /usr/sbin/sshd -t
/usr/sbin/sshd -T | awk '$1=="port" || $1=="permitrootlogin"'
run ss -ltnp
section 'Firewall'
run ufw status verbose
section 'Accounts and groups'
for account in agent-admin agent-dev agent-test; do run id "$account"; done
run getent group agent-common agent-core
section 'Directories, environment and monitor ownership'
run namei -l /home/agent-admin/agent-app/api_keys/t_secret.key
run getfacl /home/agent-admin /home/agent-admin/agent-app /home/agent-admin/agent-app/upload_files /home/agent-admin/agent-app/api_keys /var/log/agent-app
run stat -c '%U %G %a %n' /home/agent-admin/agent-app/bin/monitor.sh
run cat /home/agent-admin/agent-app/agent-env.sh
section 'Manual monitor run'
run sudo -u agent-admin -H -- /home/agent-admin/agent-app/bin/monitor.sh
section 'Recent recorded measurements'
run tail -n 10 /var/log/agent-app/monitor.log
section 'Cron registration, service and recent runs'
run crontab -u agent-admin -l
run systemctl is-active cron
run journalctl -t agent-monitor --since '10 minutes ago' --no-pager -n 30
section 'Still required separately'
echo 'Capture the provided app Boot Sequence: five [OK] lines and Agent READY.'
echo 'Record monitor.log before/after at least 70 seconds with NO manual monitor execution between snapshots.'
