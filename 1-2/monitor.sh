#!/usr/bin/env bash
# Linux /proc based interval CPU measurement; ps %cpu is lifetime average.
set -euo pipefail
pid=${1:?Usage: bash monitor.sh PID [interval_seconds]}
interval=${2:-1}
export LC_ALL=C
printf 'timestamp,pid,elapsed_s,rss_kib,cpu_pct,threads,state,log_bytes\n'
python3 - "$pid" "$interval" "${APP_LOG:-}" <<'PY'
import datetime, os, pathlib, sys, time
pid, interval, log = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
ticks = os.sysconf('SC_CLK_TCK')
start = time.monotonic()
previous = None
while True:
    try:
        stat = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if stat[0] == 'Z':
            break
        status = dict(line.split(':', 1) for line in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
        now = time.monotonic()
        cpu_ticks = int(stat[11]) + int(stat[12])
        cpu = '' if previous is None else f'{100 * (cpu_ticks-previous[0]) / ticks / (now-previous[1]):.2f}'
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')
        size = pathlib.Path(log).stat().st_size if log and pathlib.Path(log).exists() else 0
        print(f'{stamp},{pid},{now-start:.3f},{status.get("VmRSS", "0 kB").split()[0]},{cpu},{status["Threads"].strip()},{stat[0]},{size}', flush=True)
        previous = cpu_ticks, now
    except (FileNotFoundError, ProcessLookupError):
        break
    time.sleep(interval)
PY
