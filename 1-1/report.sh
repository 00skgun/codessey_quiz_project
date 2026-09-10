#!/usr/bin/env bash
# Optional bonus 1: aggregate real monitor log records.
set -euo pipefail
export LC_ALL=C
if (( $# > 3 )); then
    printf 'Usage: %s [monitor.log] ["YYYY-MM-DD HH:MM:SS" start] [end]\n' "$0" >&2
    exit 1
fi
log_file=${1:-/var/log/agent-app/monitor.log}
start=${2:-}; end=${3:-}
[[ -r $log_file && -f $log_file ]] || { printf '[ERROR] Cannot read %s\n' "$log_file" >&2; exit 1; }
for timestamp in "$start" "$end"; do
    [[ -z $timestamp ]] && continue
    [[ $timestamp =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] &&
        [[ $(date -d "$timestamp" '+%Y-%m-%d %H:%M:%S' 2>/dev/null) == "$timestamp" ]] || {
        printf '[ERROR] Invalid timestamp: %s\n' "$timestamp" >&2; exit 1;
    }
done
[[ -z $start || -z $end || ! $start > $end ]] || { printf '[ERROR] Start is after end\n' >&2; exit 1; }
awk -v start="$start" -v end="$end" '
function record(i, value, stamp) {
    sum[i]+=value
    if(n==1 || value<minimum[i]) {minimum[i]=value; min_time[i]=stamp}
    if(n==1 || value>maximum[i]) {maximum[i]=value; max_time[i]=stamp}
}
{
    # Ubuntu 22.04 mawk does not support interval quantifiers such as {4}.
    if ($0 !~ /^\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] PID:[0-9]+(,[0-9]+)* CPU:[0-9]+(\.[0-9]+)?% MEM:[0-9]+(\.[0-9]+)?% DISK_USED:[0-9]+(\.[0-9]+)?%$/) {bad++; next}
    stamp=substr($0, 2, 19)
    if((start!="" && stamp<start) || (end!="" && stamp>end)) next
    cpu=$4; mem=$5; disk=$6
    sub(/^CPU:/,"",cpu); sub(/%$/,"",cpu)
    sub(/^MEM:/,"",mem); sub(/%$/,"",mem)
    sub(/^DISK_USED:/,"",disk); sub(/%$/,"",disk)
    cpu+=0; mem+=0; disk+=0
    if(cpu>100 || mem>100 || disk>100) {bad++; next}
    n++; record(1,cpu,stamp); record(2,mem,stamp); record(3,disk,stamp)
}
END {
    print "====== STATISTICS REPORT ======"
    if(bad) printf "[WARNING] Ignored %d malformed record(s)\n",bad
    if(!n) {print "[Samples]\nData Points: 0 samples"; print "[INFO] No samples in the selected range"; exit}
    label[1]="CPU"; label[2]="Memory"; label[3]="Disk"
    for(i=1;i<=3;i++) {
        printf "[%s]\nAverage : %.1f%%\nMaximum : %.1f%% at %s\nMinimum : %.1f%% at %s\n",label[i],sum[i]/n,maximum[i],max_time[i],minimum[i],min_time[i]
    }
    printf "[Samples]\nData Points: %d samples\n",n
}' "$log_file"
