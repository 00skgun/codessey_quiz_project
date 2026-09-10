#!/usr/bin/env bash
# Isolated logic tests. Synthetic values here are NOT submission evidence.
set -euo pipefail
export LC_ALL=C
test_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$test_dir/../monitor.sh"
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
AGENT_LOG_DIR=$scratch
LOG_FILE=$scratch/monitor.log
AGENT_APP_PATH=/test/agent-app-linux-x86
AGENT_PORT=15034
count=0
pass() { count=$((count+1)); printf '[PASS] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1" >&2; [[ ! -f $scratch/output ]] || cat "$scratch/output" >&2; exit 1; }
expect() { grep -Fq -- "$2" "$1" || fail "Expected: $2"; }
find_app_pids() { echo 12345; }
listener_snapshot() { echo 'LISTEN 0 128 0.0.0.0:15034 0.0.0.0:* users:(("agent-app",pid=12345,fd=3))'; }
firewall_status() { echo 'active (test fixture)'; }
read_cpu_counters() {
    if [[ -e $scratch/cpu-read ]]; then echo '200 130'
    else touch "$scratch/cpu-read"; echo '100 50'; fi
}
memory_percent() { echo 10.0; }
disk_percent() { echo 80; }
sleep() { :; }
reset_case() { rm -f -- "$LOG_FILE" "$scratch/cpu-read"; }
reset_case
monitor_run > "$scratch/output" 2>&1 || fail 'healthy monitor'
expect "$LOG_FILE" 'PID:12345 CPU:20.0% MEM:10.0% DISK_USED:80%'
if grep -q '\[WARNING\]' "$scratch/output"; then fail 'threshold equality must not warn'; fi
pass 'healthy run: exact log format; equal thresholds do not warn'
reset_case
if (find_app_pids() { :; }; monitor_run) > "$scratch/output" 2>&1; then fail 'missing process accepted'; fi
[[ ! -e $LOG_FILE ]] || fail 'unhealthy measurement logged'
pass 'missing process fails without a success log'
reset_case
if (listener_snapshot() { :; }; monitor_run) > "$scratch/output" 2>&1; then fail 'missing listener accepted'; fi
pass 'missing TCP listener fails'
reset_case
if (listener_snapshot() { echo 'LISTEN users:(("other",pid=999,fd=3))'; }; monitor_run) > "$scratch/output" 2>&1; then fail 'other process listener accepted'; fi
pass 'unrelated listener cannot pass the app health check'
for state in inactive unknown; do
    reset_case
    (firewall_status() { echo "$state (fixture)"; }; monitor_run) > "$scratch/output" 2>&1 || fail "$state firewall halted monitor"
    expect "$scratch/output" "[WARNING] Firewall: $state"
    [[ -s $LOG_FILE ]] || fail "$state firewall prevented log"
    pass "$state firewall warns and continues"
done
reset_case
(cpu_percent() { echo 20.1; }; memory_percent() { echo 10.1; }; disk_percent() { echo 81; }; monitor_run) > "$scratch/output" 2>&1 || fail 'high resource run'
for metric in CPU MEM DISK_USED; do expect "$scratch/output" "[WARNING] $metric threshold exceeded"; done
pass 'all three strict greater-than threshold warnings'
[[ $(cpu_percent 100 50 200 130) == 20.0 ]] || fail 'CPU delta'
if cpu_percent 100 50 100 50 >/dev/null; then fail 'zero total delta accepted'; fi
pass 'CPU counter delta and invalid sample handling'
reset_case
if (memory_percent() { return 1; }; monitor_run) > "$scratch/output" 2>&1; then fail 'missing memory data accepted'; fi
[[ ! -e $LOG_FILE ]] || fail 'invalid resource sample logged'
pass 'unreadable resource fails without fabricating a sample'
reset_case
line='[2026-09-05 20:00:00] PID:12345 CPU:20.0% MEM:10.0% DISK_USED:80%'
for iteration in {1..12}; do
    truncate -s $((10*1024*1024)) "$LOG_FILE"
    append_log "$line" || fail 'log rotation'
done
shopt -s nullglob
files=("$LOG_FILE" "$LOG_FILE".[0-9]*)
[[ ${#files[@]} -eq 10 && -f $LOG_FILE.9 && ! -e $LOG_FILE.10 ]] || fail 'ten file retention'
for file in "${files[@]}"; do [[ $(stat -c %s "$file") -le $((10*1024*1024)) ]] || fail 'log size exceeded'; done
pass 'rotation after 12 cycles retains current + 9 files, each <= 10 MiB'
reset_case
exec 8>> "$AGENT_LOG_DIR/.monitor.lock"
flock -n 8
monitor_run > "$scratch/output" 2>&1 || fail 'busy lock must skip successfully'
expect "$scratch/output" 'Another monitor is running'
[[ ! -e $LOG_FILE ]] || fail 'busy lock wrote a sample'
flock -u 8
exec 8>&-
pass 'concurrent monitor skips without writing'
cat > "$scratch/report-input" <<'LOG'
[2026-09-05 10:00:00] PID:1 CPU:10.0% MEM:20.0% DISK_USED:30%
[2026-09-05 10:01:00] PID:1 CPU:30.0% MEM:40.0% DISK_USED:50%
not a measurement
LOG
bash "$test_dir/../report.sh" "$scratch/report-input" > "$scratch/output"
expect "$scratch/output" 'Average : 20.0%'
expect "$scratch/output" 'Average : 30.0%'
expect "$scratch/output" 'Average : 40.0%'
expect "$scratch/output" 'Data Points: 2 samples'
expect "$scratch/output" 'Ignored 1 malformed'
pass 'report averages CPU/MEM/DISK and excludes malformed rows'
bash "$test_dir/../report.sh" "$scratch/report-input" '2026-09-05 10:01:00' '2026-09-05 10:01:00' > "$scratch/output"
expect "$scratch/output" 'Data Points: 1 samples'
expect "$scratch/output" 'Average : 30.0%'
pass 'report includes both time range endpoints'
: > "$scratch/empty"
bash "$test_dir/../report.sh" "$scratch/empty" > "$scratch/output"
expect "$scratch/output" 'Data Points: 0 samples'
if bash "$test_dir/../report.sh" "$scratch/empty" 'invalid' >/dev/null 2>&1; then fail 'invalid date accepted'; fi
if bash "$test_dir/../report.sh" "$scratch/empty" '2026-09-06 00:00:00' '2026-09-05 00:00:00' >/dev/null 2>&1; then fail 'reversed date range accepted'; fi
pass 'empty report and invalid/reversed date ranges'
printf '\n%s tests passed. Synthetic fixtures are not real server evidence.\n' "$count"
