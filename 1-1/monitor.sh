#!/usr/bin/env bash
# 필수 과제: 상태 확인 → 자원 수집 → 경고 → 로그 기록/회전.

error() { printf '[ERROR] %s\n' "$*" >&2; }

# 제공 바이너리는 run-app.sh가 절대 경로로 실행한다.
# -f: 명령행 전체, -x: 전체 일치. 검색 명령 자체를 앱으로 오인하지 않는다.
find_app_pids() { pgrep -f -x -- "$AGENT_APP_PATH"; }
list_app_port() { ss -H -ltnp "sport = :$AGENT_PORT"; }

health_check() {
    local pids listeners pid matched=0
    pids=$(find_app_pids) || { error 'App process is not running.'; return 1; }
    [[ -n $pids ]] || { error 'App process is not running.'; return 1; }
    listeners=$(list_app_port) || { error 'Cannot inspect TCP sockets.'; return 1; }
    [[ -n $listeners ]] || { error "TCP $AGENT_PORT is not LISTENING."; return 1; }
    # 다른 프로그램이 같은 포트를 차지한 경우도 성공으로 처리하지 않는다.
    for pid in $pids; do
        [[ $listeners != *"pid=$pid,"* ]] || matched=1
    done
    (( matched )) || { error "TCP $AGENT_PORT is not owned by the app (or its PID is unreadable)."; return 1; }
    APP_PIDS=${pids//$'\n'/,}
    printf '[OK] Process PID:%s\n[OK] TCP %s LISTEN\n' "$APP_PIDS" "$AGENT_PORT"
}

ufw_status() { sudo -n /usr/sbin/ufw status; }

check_firewall() {
    local status
    if ! status=$(ufw_status 2>&1); then
        printf '[WARNING] Cannot query UFW; check the read-only sudo rule.\n'
    elif [[ $status == *'Status: active'* ]]; then
        printf '[OK] Firewall active (UFW)\n'
    else
        printf '[WARNING] Firewall inactive (UFW)\n'
    fi
    # 방화벽 경고는 치명적 오류가 아니다.
    return 0
}

read_cpu_counters() {
    # user, nice, system, idle, iowait, irq, softirq, steal만 합산.
    # guest 항목은 user 등에 이미 들어 있어 중복 합산하지 않는다.
    awk '/^cpu / {for(i=2;i<=9;i++) total+=$i; printf "%.0f %.0f\n",total,$5+$6; exit}' /proc/stat
}

cpu_from_counters() {
    # 두 시점의 누적값 차이로 1초 구간의 사용률을 구한다.
    awk -v total="$(($3-$1))" -v idle="$(($4-$2))" 'BEGIN {
        if(total<=0 || idle<0 || idle>total) exit 1
        printf "%.1f\n",100*(total-idle)/total
    }'
}

cpu_usage() {
    local total1 idle1 total2 idle2
    read -r total1 idle1 < <(read_cpu_counters) || return 1
    sleep 1
    read -r total2 idle2 < <(read_cpu_counters) || return 1
    cpu_from_counters "$total1" "$idle1" "$total2" "$idle2"
}

memory_usage() {
    awk '/^MemTotal:/ {t=$2} /^MemAvailable:/ {a=$2; found=1}
        END {if(t<=0 || !found || a<0 || a>t) exit 1; printf "%.1f\n",100*(t-a)/t}' /proc/meminfo
}

disk_usage() { df -P / | awk 'NR==2 {gsub(/%/,"",$5); print $5}'; }

warn_if_over() {
    if awk -v value="$2" -v limit="$3" 'BEGIN {exit !(value>limit)}'; then
        printf '[WARNING] %s %s%% > %s%%\n' "$1" "$2" "$3"
    fi
    return 0
}

write_log() {
    local line=$1 size=0 i
    local max_bytes=$((10*1024*1024))
    [[ ! -L $LOG_FILE ]] || { error 'Log must not be a symbolic link.'; return 1; }
    if [[ -e $LOG_FILE ]]; then
        [[ -f $LOG_FILE ]] || return 1
        size=$(stat -c %s -- "$LOG_FILE") || return 1
    fi
    # 새 줄을 더했을 때 10MiB를 초과하면 먼저 회전한다.
    if (( size + ${#line} + 1 > max_bytes )); then
        rm -f -- "$LOG_FILE.9" || return 1
        for ((i=8;i>=1;i--)); do
            if [[ -e $LOG_FILE.$i ]]; then
                mv -- "$LOG_FILE.$i" "$LOG_FILE.$((i+1))" || return 1
            fi
        done
        mv -- "$LOG_FILE" "$LOG_FILE.1" || return 1
    fi
    # 현재 로그 + .1~.9 = 총 10개. .1이 가장 최근의 백업이다.
    printf '%s\n' "$line" >> "$LOG_FILE" || return 1
}

main() (
    set -euo pipefail
    export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 0007
    local script_dir config tool cpu mem disk value
    script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    config=$script_dir/../agent-env.sh
    [[ ! -r $script_dir/agent-env.sh ]] || config=$script_dir/agent-env.sh
    if [[ -r $config ]]; then source "$config"; fi
    AGENT_HOME=${AGENT_HOME:-/home/agent-admin/agent-app}
    AGENT_APP_PATH=${AGENT_APP_PATH:-$AGENT_HOME/agent-app-linux-x86}
    AGENT_PORT=${AGENT_PORT:-15034}
    AGENT_LOG_DIR=${AGENT_LOG_DIR:-/var/log/agent-app}
    LOG_FILE=$AGENT_LOG_DIR/monitor.log
    [[ $(uname -s) == Linux ]] || { error 'Linux is required.'; return 1; }
    for tool in pgrep ss awk df stat flock date; do
        command -v "$tool" >/dev/null || { error "Missing command: $tool"; return 1; }
    done
    [[ -d $AGENT_LOG_DIR && -w $AGENT_LOG_DIR ]] || { error 'Log directory is not writable.'; return 1; }
    [[ ! -L $AGENT_LOG_DIR/.monitor.lock ]] || return 1
    exec 9>> "$AGENT_LOG_DIR/.monitor.lock"
    if ! flock -n 9; then echo '[INFO] Another monitor is running; skipped.'; return 0; fi

    printf '====== SYSTEM MONITOR RESULT ======\n[HEALTH CHECK]\n'
    health_check || return 1
    check_firewall
    cpu=$(cpu_usage) || { error 'Cannot measure CPU.'; return 1; }
    mem=$(memory_usage) || { error 'Cannot measure memory.'; return 1; }
    disk=$(disk_usage) || { error 'Cannot measure root filesystem.'; return 1; }
    for value in "$cpu" "$mem" "$disk"; do
        [[ $value =~ ^[0-9]+([.][0-9]+)?$ ]] || { error 'Invalid measurement.'; return 1; }
    done
    printf '[RESOURCES]\nCPU: %s%%\nMEM: %s%%\nDISK_USED: %s%%\n' "$cpu" "$mem" "$disk"
    warn_if_over CPU "$cpu" 20
    warn_if_over MEM "$mem" 10
    warn_if_over DISK_USED "$disk" 80
    write_log "[$(date '+%Y-%m-%d %H:%M:%S')] PID:$APP_PIDS CPU:$cpu% MEM:$mem% DISK_USED:$disk%" || {
        error 'Cannot write or rotate monitor.log.'; return 1;
    }
    printf '[INFO] Log appended: %s\n' "$LOG_FILE"
)

# source로 읽을 때는 함수만 정의하고, 직접 실행할 때만 main을 호출한다.
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
