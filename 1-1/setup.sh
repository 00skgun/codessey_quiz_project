#!/usr/bin/env bash
# Run on the Ubuntu practice machine: sudo bash setup.sh /absolute/path/to/provided-app
# Creates the assignment accounts/directories. SSH and firewall rules are handled in README.
set -euo pipefail
export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $(uname -s) == Linux && $EUID -eq 0 ]] || { echo 'Run with sudo on the Linux practice machine.' >&2; exit 1; }
[[ $# -eq 1 && -f $1 ]] || { echo "Usage: sudo bash $0 /path/to/provided-app" >&2; exit 1; }
source_app=$(readlink -f -- "$1")
app_name=${source_app##*/}
case $app_name in agent_app.py|agent-app-linux-x86|agent-app-linux-arm64) ;;
    *) echo 'Expected agent_app.py, agent-app-linux-x86, or agent-app-linux-arm64 from the assignment.' >&2; exit 1 ;;
esac
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
agent_home=/home/agent-admin/agent-app
for dependency in setfacl getfacl useradd usermod groupadd install visudo ufw ss crontab flock; do
    command -v "$dependency" >/dev/null || {
        echo "Missing $dependency. First run: sudo apt-get install acl openssh-server ufw cron python3 procps iproute2 sudo util-linux" >&2
        exit 1
    }
done
for group in agent-common agent-core; do
    getent group "$group" >/dev/null || groupadd "$group"
done
for account in agent-admin agent-dev agent-test; do
    if ! id "$account" >/dev/null 2>&1; then useradd -m -s /bin/bash "$account"; fi
    [[ $(getent passwd "$account" | cut -d: -f6) == "/home/$account" ]] || {
        echo "Existing account $account has an unexpected home; check it before continuing." >&2; exit 1;
    }
    usermod -aG agent-common "$account"
done
usermod -aG agent-core agent-admin
usermod -aG agent-core agent-dev
if id -nG agent-test | tr ' ' '\n' | grep -qx agent-core; then
    echo 'agent-test is already a member of agent-core. Remove that membership and rerun.' >&2
    exit 1
fi
# New users have locked passwords; use sudo -u for local practice.
# Do not grant blanket sudo rights to any of the three assignment accounts.
setfacl -m g:agent-common:--x /home/agent-admin
install -d -o agent-admin -g agent-common -m 2750 "$agent_home"
install -d -o root -g agent-core -m 2750 "$agent_home/bin"
install -d -o agent-admin -g agent-common -m 2770 "$agent_home/upload_files"
install -d -o agent-admin -g agent-core -m 2770 "$agent_home/api_keys" /var/log/agent-app
for directory in "$agent_home/upload_files" "$agent_home/api_keys" /var/log/agent-app; do
    # No named-user exceptions; group ownership defines access.
    setfacl -b "$directory"
    setfacl -k "$directory"
    chmod 2770 "$directory"
    setfacl -m d:u::rwx,d:g::rwx,d:m::rwx,d:o::--- "$directory"
done
if [[ -e $agent_home/api_keys/t_secret.key ]]; then
    [[ $(cat "$agent_home/api_keys/t_secret.key") == agent_api_key_test ]] || {
        echo 'Existing t_secret.key has different contents; inspect it before continuing.' >&2; exit 1;
    }
else
    printf 'agent_api_key_test\n' > "$agent_home/api_keys/t_secret.key"
fi
chown agent-admin:agent-core "$agent_home/api_keys/t_secret.key"
chmod 0660 "$agent_home/api_keys/t_secret.key"
if [[ $app_name != *.py ]]; then
    # Second PDF/binary mismatch: the binary opens secret.key, not t_secret.key.
    if [[ -e $agent_home/api_keys/secret.key || -L $agent_home/api_keys/secret.key ]]; then
        [[ $(readlink "$agent_home/api_keys/secret.key") == t_secret.key ]] || {
            echo 'Existing secret.key is not the expected compatibility link; inspect it first.' >&2; exit 1;
        }
    else
        ln -s t_secret.key "$agent_home/api_keys/secret.key"
        chown -h agent-admin:agent-core "$agent_home/api_keys/secret.key"
    fi
fi
install -o agent-admin -g agent-core -m 0750 "$source_app" "$agent_home/$app_name"
for filename in monitor.sh report.sh; do
    install -o agent-dev -g agent-core -m 0750 "$script_dir/$filename" "$agent_home/bin/$filename"
done
for filename in run-app.sh install-cron.sh; do
    install -o root -g agent-core -m 0750 "$script_dir/$filename" "$agent_home/bin/$filename"
done
env_tmp=$(mktemp)
sudoers_tmp=$(mktemp)
trap 'rm -f -- "$env_tmp" "$sudoers_tmp"' EXIT
{
    printf 'export AGENT_HOME=%q\n' "$agent_home"
    printf 'export AGENT_PORT=15034\n'
    printf 'export AGENT_UPLOAD_DIR=%q\n' "$agent_home/upload_files"
    printf 'export AGENT_KEY_PATH=%q\n' "$agent_home/api_keys/t_secret.key"
    printf 'export AGENT_LOG_DIR=/var/log/agent-app\n'
    printf 'export AGENT_APP_PATH=%q\n' "$agent_home/$app_name"
} > "$env_tmp"
install -o root -g agent-common -m 0640 "$env_tmp" "$agent_home/agent-env.sh"
# Exact read-only command only, so cron never waits for a password.
printf 'agent-admin ALL=(root) NOPASSWD: /usr/sbin/ufw status\n' > "$sudoers_tmp"
visudo -cf "$sudoers_tmp"
install -o root -g root -m 0440 "$sudoers_tmp" /etc/sudoers.d/agent-monitor-status
echo '[OK] Accounts, groups, ACLs, app, environment and scripts installed.'
echo 'Next: configure SSH/UFW in README, then run the app as agent-admin.'
