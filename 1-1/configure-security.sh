#!/usr/bin/env bash
# For the local Ubuntu practice console. Never resets unrelated firewall rules.
set -euo pipefail
export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { echo 'Run with sudo on the practice Linux machine.' >&2; exit 1; }
[[ -z ${SSH_CONNECTION:-} ]] || { echo 'Run from the local WSL/VM console so SSH changes cannot lock out this session.' >&2; exit 1; }
command -v ufw >/dev/null
[[ -x /usr/sbin/sshd && -f /etc/ssh/sshd_config ]] || { echo 'Install openssh-server first.' >&2; exit 1; }
existing_rules=$(ufw show added)
unexpected=$(printf '%s\n' "$existing_rules" | awk '/^ufw / && $0!="ufw allow 20022/tcp" && $0!="ufw allow 15034/tcp"')
[[ -z $unexpected ]] || {
    printf 'Existing firewall rules require review; no settings changed:\n%s\n' "$unexpected" >&2; exit 1;
}
if systemctl is-active --quiet ssh.socket; then
    echo 'ssh.socket is active. Check its ListenStream before switching to ssh.service.' >&2; exit 1
fi
grep -Eq '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config.d/\*\.conf' /etc/ssh/sshd_config || {
    echo 'sshd_config does not include the standard drop-in directory. Review it manually.' >&2; exit 1;
}
config=/etc/ssh/sshd_config.d/00-agent-mission.conf
backup=$(mktemp)
had_config=0
if [[ -e $config ]]; then cp -p -- "$config" "$backup"; had_config=1; fi
rollback() {
    if (( had_config )); then cp -p -- "$backup" "$config"; else rm -f -- "$config"; fi
}
trap 'rm -f -- "$backup"' EXIT
printf '# Linux assignment\nPort 20022\nPermitRootLogin no\n' > "$config"
chmod 0644 "$config"
if ! /usr/sbin/sshd -t; then rollback; exit 1; fi
effective=$(/usr/sbin/sshd -T)
ports=$(printf '%s\n' "$effective" | awk '$1=="port" {print $2}')
root_login=$(printf '%s\n' "$effective" | awk '$1=="permitrootlogin" {print $2}')
if [[ $ports != 20022 || $root_login != no ]]; then
    rollback
    echo 'Conflicting effective SSH settings; restored the previous drop-in.' >&2
    printf 'port: %s; permitrootlogin: %s\n' "$ports" "$root_login" >&2
    exit 1
fi
# Allow the target SSH port before activating the firewall.
ufw allow 20022/tcp
ufw allow 15034/tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
systemctl enable ssh
if ! systemctl restart ssh; then
    rollback
    systemctl restart ssh || true
    echo 'SSH restart failed; the SSH drop-in was restored. Inspect UFW from the local console.' >&2
    exit 1
fi
/usr/sbin/sshd -T | awk '$1=="port" || $1=="permitrootlogin"'
ss -ltnp 'sport = :20022'
ufw status verbose
