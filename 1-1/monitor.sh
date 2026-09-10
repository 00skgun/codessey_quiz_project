#!/usr/bin/env bash
# Linux system monitor. Run as agent-admin; automation is Bash + Linux utilities.

monitor_error() { printf '[ERROR] %s\n' "$*" >&2; }

find_app_pids() {
    local entry pid executable arg candidate
    local -a argv
    for entry in /proc/[0-9]*/cmdline; do
        pid=${entry#/proc/}; pid=${pid%/cmdline}
        [[ -r $entry ]] || continue
        executable=$(readlink -f "/proc/$pid/exe" 2>/dev/null) || continue
        if [[ $executable == "$AGENT_APP_PATH" ]]; then
            printf '%s\n' "$pid"
            continue
        fi
        case ${executable##*/} in python*|pypy*) ;; *) continue ;; esac
        argv=()
        mapfile -d '' -t argv < "$entry" 2>/dev/null || continue
        # Match the Python script argument, not a substring in a grep/shell command.
        for arg in "${argv[@]:1}"; do
            [[ $arg == -c || $arg == -m ]] && break
            [[ $arg == *.py ]] || continue
            candidate=$arg
            [[ $arg == /* ]] || candidate="/proc/$pid/cwd/$arg"
            candidate=$(readlink -f -- "$candidate" 2>/dev/null) || break
            [[ $candidate != "$AGENT_APP_PATH" ]] || printf '%s\n' "$pid"
            break
        done
    done
}

listener_snapshot() { ss -H -ltnp "sport = :$AGENT_PORT"; }

read_cpu_counters() {
    local label user nice system idle iowait irq softirq steal rest
    read -r label user nice system idle iowait irq softirq steal rest < /proc/stat
    [[ $label == cpu ]] || return 1
    # guest/guest_nice are already included in user/nice; do not count them twice.
    printf '%s %s\n' "$((user + nice + system + idle + iowait + irq + softirq + steal))" "$((idle + iowait))"
}

cpu_percent() {
    local total_before=$1 idle_before=$2 total_after=$3 idle_after=$4
    awk -v t="$((total_after - total_before))" -v i="$((idle_after - idle_before))" 'BEGIN {
        if (t <= 0 || i < 0 || i > t) exit 1
        printf "%.1f\n", 100 * (t-i) / t
    }'
}

memory_percent() {
    awk '/^MemTotal:/ {t=$2} /^MemAvailable:/ {a=$2; found=1}
        END {if(t<=0 || !found || a<0 || a>t) exit 1; printf "%.1f\n", 100*(t-a)/t}' /proc/meminfo
}

disk_percent() { df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}'; }

firewall_status() {
    local result
    if command -v ufw >/dev/null 2>&1; then
        if (( EUID == 0 )); then
            result=$(ufw status 2>&1) || { printf 'unknown (ufw query failed)\n'; return; }
        else
            result=$(sudo -n /usr/sbin/ufw status 2>&1) || {
                printf 'unknown (allow agent-admin to run only /usr/sbin/ufw status)\n'; return;
            }
        fi
        if [[ $result == *'Status: active'* ]]; then printf 'active (ufw)\n'
        else printf 'inactive (ufw)\n'; fi
    elif command -v firewall-cmd >/dev/null 2>&1; then
        if result=$(firewall-cmd --state 2>&1); then
            [[ $result != running ]] || { printf 'active (firewalld)\n'; return; }
            printf 'unknown (firewalld response)\n'
        elif [[ $result == *'not running'* ]]; then printf 'inactive (firewalld)\n'
        else printf 'unknown (firewalld query failed)\n'; fi
    else
        printf 'unknown (no supported firewall command)\n'
    fi
}

warn_threshold() {
    if awk -v actual="$2" -v limit="$3" 'BEGIN {exit !(actual > limit)}'; then
        printf '[WARNING] %s threshold exceeded (%s%% > %s%%)\n' "$1" "$2" "$3"
    fi
    return 0
}

append_log() {
    local line=$1 size=0 index
    local max_bytes=$((10 * 1024 * 1024))
    # Call while holding .monitor.lock. Ten files total: current + nine backups.
    [[ ! -L $LOG_FILE ]] || { monitor_error 'Refusing a symlink log file'; return 1; }
    if [[ -e $LOG_FILE ]]; then
        [[ -f $LOG_FILE ]] || { monitor_error 'Log path is not a regular file'; return 1; }
        size=$(stat -c '%s' -- "$LOG_FILE") || return 1
    fi
    if (( size + ${#line} + 1 > max_bytes )); then
        for ((index=9; index>=1; index--)); do
            [[ ! -L $LOG_FILE.$index ]] || { monitor_error 'Refusing a symlink backup'; return 1; }
            [[ ! -e $LOG_FILE.$index || -f $LOG_FILE.$index ]] || return 1
        done
        rm -f -- "$LOG_FILE.9" || return 1
        for ((index=8; index>=1; index--)); do
            if [[ -f $LOG_FILE.$index ]]; then
                mv -- "$LOG_FILE.$index" "$LOG_FILE.$((index+1))" || return 1
            fi
        done
        mv -- "$LOG_FILE" "$LOG_FILE.1" || return 1
    fi
    printf '%s\n' "$line" >> "$LOG_FILE" || return 1
}

monitor_run() (
    # Subshell releases the lock even when returning early.
    local pids listeners pid fw total_before idle_before total_after idle_after
    local cpu mem disk line matched=0
    [[ -d $AGENT_LOG_DIR && -w $AGENT_LOG_DIR ]] || {
        monitor_error "Log directory is missing or not writable: $AGENT_LOG_DIR"; return 1;
    }
    [[ ! -L $AGENT_LOG_DIR/.monitor.lock ]] || return 1
    exec 9>> "$AGENT_LOG_DIR/.monitor.lock" || return 1
    if ! flock -n 9; then printf '[INFO] Another monitor is running; skipped.\n'; return 0; fi
    printf '====== SYSTEM MONITOR RESULT ======\n[HEALTH CHECK]\n'
    pids=$(find_app_pids) || { monitor_error 'Cannot inspect processes'; return 1; }
    [[ -n $pids ]] || { monitor_error "App is not running: $AGENT_APP_PATH"; return 1; }
    pids=${pids//$'\n'/,}
    printf 'Process %s... [OK] (PID: %s)\n' "${AGENT_APP_PATH##*/}" "$pids"
    listeners=$(listener_snapshot) || { monitor_error 'Cannot inspect TCP listeners'; return 1; }
    [[ -n $listeners ]] || { monitor_error "TCP $AGENT_PORT is not LISTENING"; return 1; }
    # All app processes run as agent-admin, so ss can show their socket ownership.
    local -a pid_list
    IFS=, read -r -a pid_list <<< "$pids"
    for pid in "${pid_list[@]}"; do
        [[ $listeners != *"pid=$pid,"* ]] || matched=1
    done
    (( matched )) || { monitor_error "TCP $AGENT_PORT is not owned by the app (or PID is not visible)"; return 1; }
    printf 'TCP %s LISTEN... [OK]\n' "$AGENT_PORT"
    fw=$(firewall_status)
    if [[ $fw == active* ]]; then printf 'Firewall... [OK] %s\n' "$fw"
    else printf '[WARNING] Firewall: %s\n' "$fw"; fi
    read -r total_before idle_before < <(read_cpu_counters)
    [[ -n $total_before && -n $idle_before ]] || return 1
    sleep 1
    read -r total_after idle_after < <(read_cpu_counters)
    [[ -n $total_after && -n $idle_after ]] || return 1
    cpu=$(cpu_percent "$total_before" "$idle_before" "$total_after" "$idle_after") || {
        monitor_error 'Invalid CPU sample'; return 1;
    }
    mem=$(memory_percent) || { monitor_error 'Cannot read memory usage'; return 1; }
    disk=$(disk_percent) || { monitor_error 'Cannot read root filesystem usage'; return 1; }
    for line in "$cpu" "$mem" "$disk"; do
        [[ $line =~ ^[0-9]+([.][0-9]+)?$ ]] || { monitor_error 'Invalid resource measurement'; return 1; }
    done
    printf '[RESOURCE MONITORING]\nCPU Usage : %s%%\nMEM Usage : %s%%\nDISK Used : %s%%\n' "$cpu" "$mem" "$disk"
    warn_threshold CPU "$cpu" 20
    warn_threshold MEM "$mem" 10
    warn_threshold DISK_USED "$disk" 80
    line="[$(date '+%Y-%m-%d %H:%M:%S')] PID:$pids CPU:$cpu% MEM:$mem% DISK_USED:$disk%"
    append_log "$line" || { monitor_error "Cannot append log: $LOG_FILE"; return 1; }
    printf '[INFO] Log appended: %s\n' "$LOG_FILE"
)

monitor_main() {
    set -uo pipefail
    export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 0007
    local script_dir dependency
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    if [[ -f $script_dir/../agent-env.sh ]]; then source "$script_dir/../agent-env.sh"; fi
    : "${AGENT_HOME:=/home/agent-admin/agent-app}"
    : "${AGENT_APP_PATH:=$AGENT_HOME/agent_app.py}"
    : "${AGENT_PORT:=15034}"
    : "${AGENT_LOG_DIR:=/var/log/agent-app}"
    LOG_FILE=$AGENT_LOG_DIR/monitor.log
    [[ $AGENT_PORT =~ ^[0-9]+$ ]] && (( AGENT_PORT >= 1 && AGENT_PORT <= 65535 )) || {
        monitor_error 'Invalid AGENT_PORT'; return 1;
    }
    [[ $(uname -s) == Linux ]] || { monitor_error 'Run this script on Linux'; return 1; }
    for dependency in ss awk df stat readlink flock date sleep; do
        command -v "$dependency" >/dev/null || { monitor_error "Missing command: $dependency"; return 1; }
    done
    AGENT_APP_PATH=$(readlink -f -- "$AGENT_APP_PATH") || return 1
    monitor_run
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then monitor_main "$@"; fi
