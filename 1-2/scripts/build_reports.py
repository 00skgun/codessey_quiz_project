#!/usr/bin/env python3
"""Create Markdown evidence excerpts and standalone SVG charts from captured data."""
import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports'
IMAGES = ROOT / 'docs' / 'images'

def read(name):
    p = ROOT / 'evidence' / name
    return dict(name=name, result=json.loads((p/'result.json').read_text()),
                rows=list(csv.DictReader((p/'metrics.csv').open())),
                log=(p/'app.log').read_text(), system=(p/'system.log').read_text())

def outcome(d):
    if 'Memory limit exceeded' in d['log']:
        return 'MemoryGuard 강제 종료'
    if 'WATCHDOG' in d['log'] and 'SIGTERM' in d['log']:
        return 'Watchdog SIGTERM 종료'
    if 'CPU Threshold Violated' in d['log'] and not d['result']['harness_stopped']:
        return 'CPU 임계치 위반 후 SIGTERM (Watchdog 문구는 원본 참조)'
    if d['result']['alive_at_window_end']:
        if 'WAITING for [Shared_Memory_A]' in d['log'] and 'WAITING for [Socket_Pool_B]' in d['log']:
            return '교착 정체 (PID 생존, 수집기가 정리)'
        return '관측 창 종료까지 PID 생존 (수집기가 정리)'
    return '앱 로그 참조'

def stats(d):
    rows = d['rows']
    return max(float(r['rss_kib'])/1024 for r in rows), max(float(r['cpu_pct'] or 0) for r in rows)

def chart(path, title, datasets, fields, x_label='Elapsed seconds since monitoring began'):
    # Plot actual points without interpolating missing tails or invented termination values.
    width, height = 1000, 110 + 230 * len(fields)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#f8fafc"/>',
             '<g font-family="Arial, sans-serif" fill="#0f172a">',
             f'<text x="36" y="34" font-size="22" font-weight="bold">{html.escape(title)}</text>']
    colors = ['#2563eb', '#e05b23']
    for i,d in enumerate(datasets):
        config=d['result']['config']
        setting=(config['MEMORY_LIMIT']+' MB') if d['name'].startswith('oom') else (config['CPU_MAX_OCCUPY']+'%') if d['name'].startswith('cpu') else ('threads='+config['MULTI_THREAD_ENABLE'])
        parts.append(f'<text x="{36+i*460}" y="62" fill="{colors[i]}" font-size="14">{html.escape(d["name"])} | {setting} | PID {d["result"]["pid"]}</text>')
    xmax = max(float(r['elapsed_s']) for d in datasets for r in d['rows']) or 1
    for pane,(field,label,scale) in enumerate(fields):
        top, left, w, h = 108+230*pane, 88, 860, 155
        ymax = max(float(r[field] or 0)*scale for d in datasets for r in d['rows']) * 1.12 or 1
        parts.append(f'<text x="36" y="{top-14}" font-size="15" font-weight="bold">{html.escape(label)}</text>')
        for j in range(5):
            y, value = top+h-j*h/4, ymax*j/4
            parts.append(f'<path d="M{left},{y}h{w}" stroke="#dbe2ea"/><text x="{left-10}" y="{y+4}" text-anchor="end" font-size="12">{value:.1f}</text>')
            x = left+j*w/4
            parts.append(f'<text x="{x}" y="{top+h+20}" text-anchor="middle" font-size="12">{xmax*j/4:.1f}</text>')
        parts.append(f'<text x="{left+w}" y="{top+h+40}" text-anchor="end" font-size="12">{html.escape(x_label)}</text>')
        for i,d in enumerate(datasets):
            points = [(left+float(r['elapsed_s'])/xmax*w, top+h-float(r[field])*scale/ymax*h) for r in d['rows'] if r[field]!='']
            coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{colors[i]}" stroke-width="2.3"/>')
            if points:
                x,y=points[-1]
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{colors[i]}"/>')
    parts.extend(['</g>', '</svg>'])
    path.write_text('\n'.join(parts), encoding='utf-8')

def evidence(d, pattern):
    result=d['result']
    lines=[line for line in d['log'].splitlines() if re.search(pattern,line)]
    # Preserve start and final messages, including the whole deadlock acquisition chain.
    if len(lines)>24:
        lines=lines[:6]+['... (중간 생략: 원본 app.log 참조) ...']+lines[-18:]
    return f'''### {d['name']} (앱 PID {result['pid']}, 실행기 PID {result['launcher_pid']})

![{d['name']} 저장 로그 캡처](../docs/log-captures/{d['name']}.png)

- 시작 UTC: `{result['started_at']}`
- 종료/관측 종료 UTC: `{result['ended_at']}`
- 관측 시간: **{result['observation_seconds']:.3f}초**
- 판정: **{outcome(d)}** / returncode `{result['returncode']}` / 수집기 종료 `{result['harness_stopped']}`
- [실행 로그](../evidence/{d['name']}/app.log), [관제 CSV](../evidence/{d['name']}/metrics.csv), [ps·top 출력](../evidence/{d['name']}/system.log), [설정 및 결과](../evidence/{d['name']}/result.json)

```text
{chr(10).join(lines)}
```
'''

def table(data):
    text='| 실행 ID | 앱 PID | 관측 초 | 최대 RSS MiB | 최대 구간 CPU % | 결과 |\n|---|---:|---:|---:|---:|---|\n'
    for d in data:
        mem,cpu=stats(d)
        text+=f"| {d['name']} | {d['result']['pid']} | {d['result']['observation_seconds']:.3f} | {mem:.1f} | {cpu:.2f} | {outcome(d)} |\n"
    return text

def build():
    OUT.mkdir(exist_ok=True)
    IMAGES.mkdir(parents=True,exist_ok=True)
    names=['oom-before','oom-after','cpu-before','cpu-after','deadlock-before','deadlock-after']
    data=[read(name) for name in names]
    for key,pair,fields in [
        ('oom',data[:2],[('rss_kib','Resident memory (MiB)',1/1024)]),
        ('cpu',data[2:4],[('cpu_pct','Interval CPU (% of one core)',1)]),
        ('deadlock',data[4:],[('rss_kib','Resident memory (MiB)',1/1024),('log_bytes','Captured stdout size (bytes)',1)])]:
        chart(IMAGES/f'{key}.svg', f'{key.upper()} | measured Before / After',pair,fields)
    internal=[]
    for d in data[2:4]:
        points=[]
        first=None
        for line in d['log'].splitlines():
            m=re.search(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+) .*Current Load: ([\d.]+)%',line)
            if m:
                from datetime import datetime
                t=datetime.strptime(m[1],'%Y-%m-%d %H:%M:%S,%f')
                first=first or t
                points.append(dict(elapsed_s=(t-first).total_seconds(),cpu_pct=m[2]))
        internal.append(dict(name=d['name'],result=d['result'],rows=points))
    chart(IMAGES/'cpu-reported.svg','CPU | application-reported load (not OS CPU)',internal,[('cpu_pct','Current Load from application log (%)',1)],'Elapsed seconds since first Current Load record')
    (OUT/'comparison.md').write_text('# 실제 실행 비교\n\n'+table(data)+'\n관측 시간은 실행기 시작 기준이며 종료 확인 주기 약 2초와 명령 실행 시간이 포함된다. 그래프 시간은 관제 시작 기준이다. 수집기 종료는 자연 종료가 아니며, 실제 생존 시간의 하한이다. CSV는 UTC, 앱은 KST다. 구간 CPU와 앱의 내부 부하 표시는 같은 지표가 아니다.\n',encoding='utf-8')
    specs=[
      ('01-oom.md','OOM - 메모리 한도 도달 시 MemoryGuard 강제 종료',data[:2],
       '메모리가 시간에 따라 계단 형태로 증가한 뒤 앱 MemoryGuard가 종료했다. MEMORY_LIMIT 외 설정을 고정하고 50MB와 200MB를 비교했다.',
       'MemoryWorker|MemoryGuard|SELF-TERMINATED',
       '각 실행에서 Current Heap가 일정량씩 증가하고 MemoryGuard의 한도 초과 및 대상 PID 종료 로그가 이어진다. RSS도 함께 증가한다. 이는 메모리 누적과 앱 보호 정책에 의한 종료를 뒷받침한다. 외부 관측만으로 누수를 만드는 객체나 소스 위치는 확정할 수 없다. 이 종료를 커널 OOM killer 동작으로 단정하지 않는다.',
       'MEMORY_LIMIT를 50 → 200MB로 높이면 더 오래 생존했으나 결국 같은 정책으로 종료했다. 메모리 누수의 근본 해결이 아닌 임시 조치다. 두 실행의 환경변수 CPU_MAX_OCCUPY=100, MULTI_THREAD_ENABLE=false는 동일하다.'),
      ('02-cpu.md','CPU - 작업 부하 설정 변화와 Watchdog 보호 종료 비교',data[2:4],
       'CPU_MAX_OCCUPY=10%와 100%를 비교했다. 실행 ID cpu-before는 10%, cpu-after는 100%인 실험 순서를 뜻한다. 개선 조치는 높은 설정에서 낮은 설정으로 되돌리는 방향이며, Before/After 이름만으로 성공 여부를 판단하지 않는다.',
       'CpuWorker|WATCHDOG|SIGTERM|EMERGENCY|Current Load|CPU Usage|Critical',
       'CpuWorker 로그의 Current Load와 외부 관제 CPU는 측정 방식이 다르다. 이 바이너리에서는 설정값이 Maximum CPU Limit와 부하 증가·cooldown 동작에 관여하는 것이 관측된다. 보호 종료 여부는 WATCHDOG와 SIGTERM 메시지를 근거로 판단한다. 종료 코드 -15만으로 Watchdog를 확정하면 수집기의 SIGTERM을 혼동할 수 있다.',
       '임시 조치는 CPU_MAX_OCCUPY를 100 → 10으로 낮추는 것이다. 아래 두 실행으로 종료 여부와 생존 시간을 비교한다. MEMORY_LIMIT=512, MULTI_THREAD_ENABLE=false는 고정했다. 구간 CPU 표본의 최고치는 짧은 순간 급등을 놓칠 수 있으며 내부 정책 임계치의 정확한 식은 역분석하지 않았다.'),
      ('03-deadlock.md','Deadlock - 멀티스레드 락 대기와 단일 스레드 회피 비교',data[4:],
       'MULTI_THREAD_ENABLE=true에서 PID가 살아 있으나 CPU/RSS와 로그 출력이 정체됐다. false에서는 작업과 자원 로그가 계속 진행됐다. 반복 스냅샷과 마지막 락 로그를 연결해 비교했다.',
       'Thread|Worker|LOCK|Lock|lock|WAIT|BLOCK|acquir|Acquir|deadlock|Deadlock',
       'Worker-Thread-1은 Shared_Memory_A를 획득한 뒤 Socket_Pool_B를 기다리고, Worker-Thread-2는 Socket_Pool_B를 획득한 뒤 Shared_Memory_A를 기다린다. 각 락을 하나의 스레드만 갖는 상호 배제, 보유한 채 기다리는 점유 대기, 강제로 빼앗지 않는 비선점, 상대의 락을 기다리는 순환 대기가 함께 성립하는 구조다. 실제 ps -L에서 메인 스레드와 두 작업 스레드는 futex_wait_queue에서 대기했고 마지막 10초 RSS·로그 크기가 일정하며 구간 CPU는 0%였다. ps의 S 상태나 futex 대기만으로는 교착을 확정할 수 없어 락 로그와 진행 정체를 결합했다.',
       'MULTI_THREAD_ENABLE을 true → false로 바꾸고 진행 로그·RSS·CPU 변화를 비교했다. MEMORY_LIMIT=512와 CPU_MAX_OCCUPY=10은 고정해 CPU 보호 종료의 간섭을 피했다. 단일 스레드로 순환 락 경쟁을 피하더라도 다른 장애까지 해결한 것은 아니다.')]
    for file,title,pair,desc,pattern,cause,action in specs:
        content=f'# [Bug] {title}\n\n## 1. Description (현상 설명)\n\n{desc}\n\n## 2. Evidence & Logs (증거 자료)\n\n'+table(pair)+'\n'+''.join(evidence(d,pattern) for d in pair)
        if file.startswith('03'):
            d=pair[0]
            content+='\n### 락 소유·대기 관계\n\n| 스레드 | 이미 획득한 자원 | 추가로 기다리는 자원 | 로그 상태 |\n|---|---|---|---|\n| Worker-Thread-1 | Shared_Memory_A | Socket_Pool_B | WAITING / BLOCKED |\n| Worker-Thread-2 | Socket_Pool_B | Shared_Memory_A | WAITING / BLOCKED |\n\nThread-1 → Socket_Pool_B → Thread-2 → Shared_Memory_A → Thread-1의 순환이 형성된다. 위의 원본 발췌에서 LOCK ACQUIRED와 WAITING 시각을 연결한 결과다.\n'
            # Show tail of repeated thread observations, not only a claimed interpretation.
            content+='\n### 마지막 스레드·프로세스 스냅샷 (UTC)\n\n```text\n'+'\n'.join(d['system'].splitlines()[-65:])+'\n```\n'
            rows=d['rows']
            tail=[r for r in rows if float(r['elapsed_s'])>=float(rows[-1]['elapsed_s'])-10]
            content+='\n### 마지막 10초 정체 관측\n\n| UTC | PID | RSS KiB | 구간 CPU % | 로그 bytes |\n|---|---:|---:|---:|---:|\n'
            for r in tail[::4]:
                content+=f"| {r['timestamp']} | {r['pid']} | {r['rss_kib']} | {r['cpu_pct']} | {r['log_bytes']} |\n"
        content+=f'\n## 3. Root Cause Analysis (원인 분석)\n\n{cause}\n\n## 4. Workaround & Verification (조치 및 검증)\n\n{action}\n\n측정은 조건당 1회이며, 75초 관측 창 종료 시에는 수집기가 시작한 프로세스 그룹에 SIGTERM을 보낸다. `harness_stopped=true`는 앱 자체 종료 증거로 사용하지 않는다. 원본 로그의 종료 문구를 우선한다.\n'
        if file.startswith('01'):
            a,b=[d['result']['observation_seconds'] for d in pair]
            content+=f'\n**검증 결론:** 50MB에서 {a:.3f}초, 200MB에서 {b:.3f}초 관측 후 종료를 확인했다. 종료 직전 로그가 각각 50MB/200MB 도달을 기록하며 두 실행 모두 SELF-TERMINATED다. 생존 시간은 약 {b/a:.2f}배 늘었지만 영구 해결은 아니다.\n'
        elif file.startswith('02'):
            low,high=[d['result']['observation_seconds'] for d in pair]
            content+=f'\n### 조치 관점의 Before & After\n\n| 구분 | 설정 | 실행 ID | 관측 결과 |\n|---|---|---|---|\n| 조치 전 장애 조건 | CPU_MAX_OCCUPY=100 | cpu-after | {high:.3f}초 관측 후 Watchdog 종료 확인 |\n| 조치 후 완화 조건 | CPU_MAX_OCCUPY=10 | cpu-before | 최소 {low:.3f}초 생존, 관측 창 종료 후 수집기가 정리 |\n\n실험은 낮은 설정을 먼저 실행했다. 위 표는 실제 수행 시점을 바꾸지 않고, 장애 조건과 완화 조건을 조치 관점에서 배치한 것이다.\n'
            content+='\n**검증 결론:** 100% 설정에서는 앱 부하가 50%를 넘은 뒤 CPU Threshold Violated 및 WATCHDOG SIGTERM 로그로 종료했다. 10% 설정에서는 부하 증가·cooldown 로그가 이어졌고 관측 창까지 생존했다. 따라서 완화 방향은 100 → 10%다. 외부 관제 CPU는 앱이 보고한 부하와 같은 비율로 상승하지 않았으므로, 이 자료가 실제 OS CPU 50% 초과를 입증한다고 주장하지 않는다.\n'
            content+=f'\n외부 구간 CPU 최대 관측값은 10% 설정에서 {stats(pair[0])[1]:.2f}%, 100% 설정에서 {stats(pair[1])[1]:.2f}%였다. 따라서 실제 OS CPU 과점유 재현이라는 평가 요소에는 이 한계를 함께 제시해야 한다. 원본을 변경하거나 별도 부하를 만들어 제공 앱의 사용률로 제시하지 않았다.\n'
        else:
            content+='\n**검증 결론:** true에서 상반된 락 소유·대기와 정체를 관측했다. false에서는 같은 순환 대기 없이 작업 완료와 메모리·CPU 로그가 계속 진행됐고 메모리 캐시 정리 후 다시 증가하는 동작도 관측됐다. 두 실행은 수집기 종료 전까지의 관측이며 장기 무장애를 보장하지 않는다.\n'
        (OUT/file).write_text(content,encoding='utf-8')
    print('Generated 3 reports, comparison table and 4 SVG charts from 6 runs.')

if __name__=='__main__':
    build()
