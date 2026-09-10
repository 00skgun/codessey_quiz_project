#!/usr/bin/env bash
# Complete the prepared assignment on this local Ubuntu instance and capture real evidence.
set -euo pipefail
export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { echo 'Run as root on the local Ubuntu practice machine.' >&2; exit 1; }
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$project"
[[ -f provided/agent-app-linux-x86 ]] || { echo 'Missing provided x86 app.' >&2; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'This invocation expects an x86_64 machine.' >&2; exit 1; }
mkdir -p evidence
exec > >(tee evidence/apply-session.txt) 2>&1
date --iso-8601=seconds
apt_options=(-o Acquire::ForceIPv4=true -o Acquire::Retries=0 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
if [[ ! -x /usr/sbin/sshd ]] || ! command -v setfacl >/dev/null || ! command -v pdftoppm >/dev/null; then
    apt-get "${apt_options[@]}" update
    apt-get "${apt_options[@]}" install -y acl openssh-server ufw cron python3 procps iproute2 sudo util-linux poppler-utils
fi
if systemctl is-failed --quiet agent-app; then
    journalctl -u agent-app -b --no-pager >> evidence/boot-before-compatibility-fix.txt
fi
bash setup.sh "$project/provided/agent-app-linux-x86"
bash verify-permissions.sh | tee evidence/permissions.txt
bash configure-security.sh | tee evidence/security.txt
install -o root -g root -m 0644 agent-app.service /etc/systemd/system/agent-app.service
systemctl daemon-reload
systemctl enable agent-app
systemctl restart agent-app
sleep 3
if ! systemctl is-active --quiet agent-app; then
    journalctl -u agent-app -b --no-pager -n 40
    exit 1
fi
invocation=$(systemctl show -p InvocationID --value agent-app)
journalctl "_SYSTEMD_INVOCATION_ID=$invocation" --no-pager | tee evidence/boot.txt
sudo -u agent-admin -H -- /home/agent-admin/agent-app/bin/monitor.sh | tee evidence/monitor.txt
systemctl enable --now cron
sudo -u agent-admin -H -- /home/agent-admin/agent-app/bin/install-cron.sh | tee evidence/crontab.txt
{
    echo 'BEFORE (no manual monitor execution during the following 70 seconds)'
    date --iso-8601=seconds
    before=$(stat -c %s /var/log/agent-app/monitor.log)
    wc -l /var/log/agent-app/monitor.log
    tail -n 1 /var/log/agent-app/monitor.log
    sleep 70
    echo 'AFTER'
    date --iso-8601=seconds
    after=$(stat -c %s /var/log/agent-app/monitor.log)
    wc -l /var/log/agent-app/monitor.log
    tail -n 3 /var/log/agent-app/monitor.log
    [[ $after -gt $before ]] || { echo '[FAIL] No automatic log growth.'; exit 1; }
    echo '[OK] Log grew while no manual monitor was run.'
    journalctl -t agent-monitor --since '3 minutes ago' --no-pager
} | tee evidence/cron-auto.txt
bash collect-evidence.sh > evidence/system.txt 2>&1
sudo -u agent-admin -H -- /home/agent-admin/agent-app/bin/report.sh | tee evidence/report.txt
sudo -u agent-admin -H -- cat /var/log/agent-app/monitor.log > evidence/monitor.log.txt
echo '[OK] Prepared assignment applied. Review the captured evidence before submission.'
