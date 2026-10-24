#!/usr/bin/env python3
"""Check captured evidence consistency; does not claim all rubric items passed."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from build_reports import read

ROOT=Path(__file__).resolve().parents[1]
names=['oom-before','oom-after','cpu-before','cpu-after','deadlock-before','deadlock-after']
data={name:read(name) for name in names}
for name,d in data.items():
    rows=d['rows']
    assert len(rows)>5, name
    assert all(int(r['pid'])==d['result']['pid'] for r in rows), name
    assert all(float(a['elapsed_s'])<float(b['elapsed_s']) for a,b in zip(rows,rows[1:])), name
    assert f'application_pid={d["result"]["pid"]}' in d['system'], name
    assert 'All Boot Checks Passed!' in d['log'], name
for prefix,key in [('oom','MEMORY_LIMIT'),('cpu','CPU_MAX_OCCUPY'),('deadlock','MULTI_THREAD_ENABLE')]:
    a,b=[data[f'{prefix}-{suffix}']['result']['config'] for suffix in ['before','after']]
    keys=['MEMORY_LIMIT','CPU_MAX_OCCUPY','MULTI_THREAD_ENABLE']
    assert [k for k in keys if a[k]!=b[k]]==[key], prefix
for name in ['oom-before','oom-after']:
    d=data[name]
    assert 'Memory limit exceeded' in d['log'] and 'SELF-TERMINATED' in d['log']
    assert f'Self-terminating process {d["result"]["pid"]}' in d['log']
    assert not d['result']['harness_stopped']
assert data['oom-after']['result']['observation_seconds']>data['oom-before']['result']['observation_seconds']
assert 'WATCHDOG: INITIATING EMERGENCY ABORT (SIGTERM)' in data['cpu-after']['log']
assert not data['cpu-after']['result']['harness_stopped']
assert data['cpu-before']['result']['alive_at_window_end']
d=data['deadlock-before']
assert d['result']['alive_at_window_end']
for text in ['LOCK ACQUIRED: [Shared_Memory_A]','LOCK ACQUIRED: [Socket_Pool_B]',
             'WAITING for [Shared_Memory_A]','WAITING for [Socket_Pool_B]']:
    assert text in d['log'], text
tail=[r for r in d['rows'] if float(r['elapsed_s'])>=float(d['rows'][-1]['elapsed_s'])-10]
assert len({r['rss_kib'] for r in tail})==1
assert len({r['log_bytes'] for r in tail})==1
assert max(float(r['cpu_pct'] or 0) for r in tail)<1
assert 'WAITING for [Socket_Pool_B]' not in data['deadlock-after']['log']
assert 'Current Heap' in data['deadlock-after']['log']
assert data['deadlock-after']['result']['alive_at_window_end']
for p in (ROOT/'docs/images').glob('*.svg'):
    ET.parse(p)
for p in [ROOT/'README.md',*list((ROOT/'reports').glob('*.md'))]:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if not re.match(r'\w+://',target) and not target.startswith('#'):
            assert (p.parent/target.split('#')[0]).exists(), (p,target)
print('PASS: 6 runs, PID/time consistency, one-variable comparisons, OOM/Watchdog logs,')
print('deadlock lock cycle and stalled final 10 seconds, recovery progress, SVG XML and local links.')
print('LIMITATION: application-reported CPU load is not equivalent to measured OS CPU usage.')
