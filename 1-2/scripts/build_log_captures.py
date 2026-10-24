#!/usr/bin/env python3
"""Build honest saved-log viewers for browser PNG capture; never recreate terminal output."""
import argparse
import html
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs' / 'log-captures'
NAMES = ['oom-before', 'oom-after', 'cpu-before', 'cpu-after', 'deadlock-before', 'deadlock-after']

def numbered(lines):
    return '\n'.join(f'{number:>4}  {line}' for number,line in lines)

def build():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest=[]
    for name in NAMES:
        folder=ROOT/'evidence'/name
        result=json.loads((folder/'result.json').read_text())
        all_lines=list(enumerate((folder/'app.log').read_text().splitlines(),1))
        if name.startswith('oom'):
            selected=[p for p in all_lines if any(k in p[1] for k in ['Current Heap','MemoryGuard','SELF-TERMINATED'])]
        elif name=='cpu-after':
            selected=[p for p in all_lines if any(k in p[1] for k in ['Current Load','Threshold Violated','WATCHDOG'])]
        elif name=='deadlock-before':
            selected=[p for p in all_lines if any(k in p[1] for k in ['[Worker-Thread','WAITING','LOCK ACQUIRED','Waiting for worker'])]
        else:
            selected=[p for p in all_lines if any(k in p[1] for k in ['Current Heap','Current Load','Cache Flushed','MEMORY RECOVERED','Task Completed'])][-14:]
        app=numbered(selected)
        # Keep CSV values and column names byte-for-byte, including UTC timestamps.
        metric_lines=(folder/'metrics.csv').read_text().splitlines()
        metrics='\n'.join([metric_lines[0],*metric_lines[-6:]])
        system=(folder/'system.log').read_text().splitlines()
        starts=[i for i,line in enumerate(system) if line.startswith('SNAPSHOT ')]
        i=starts[-1]
        ending=next((j for j in range(i+1,len(system)) if system[j].startswith('top -')),len(system))
        snapshot='\n'.join(system[i:ending]).strip()
        config=result['config']
        settings=' | '.join(f'{k}={config[k]}' for k in ['MEMORY_LIMIT','CPU_MAX_OCCUPY','MULTI_THREAD_ENABLE'])
        blocks=[('app.log — 原文行番号 / 원본 줄 번호',app),('metrics.csv — 마지막 6개 표본 (UTC)',metrics),('system.log — 마지막 ps 스냅샷 (UTC)',snapshot)]
        body=''.join(f'<section><h2>{html.escape(title)}</h2><pre>{html.escape(content)}</pre></section>' for title,content in blocks)
        height=330+sum(72+21*sum(max(1,math.ceil(len(line)/140)) for line in content.splitlines()) for _,content in blocks)
        page=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>{name} | Saved evidence</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#0b1220;color:#dbeafe;font:15px/1.5 Arial,"Malgun Gothic",sans-serif}}main{{padding:28px 32px;width:1360px}}.badge{{color:#7dd3fc;font-size:13px;letter-spacing:1px}}h1{{margin:8px 0;font-size:27px;color:#fff}}p{{margin:6px 0;color:#a8bbd4}}.meta{{padding:12px 16px;background:#152238;border-left:4px solid #38bdf8;margin:18px 0}}h2{{font-size:14px;margin:0;padding:10px 14px;color:#93c5fd;background:#18263b}}section{{margin:16px 0;border:1px solid #30435f;border-radius:8px;overflow:hidden}}pre{{margin:0;padding:14px;font:14px/21px Consolas,"Courier New",monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:#e2e8f0}}footer{{color:#94a3b8;font-size:13px;margin-top:20px}}</style>
<main><div class="badge">SAVED LOG EVIDENCE · 저장 로그 발췌 화면</div><h1>{name} · Application PID {result['pid']}</h1>
<p>실제 실행 로그를 읽기 전용 HTML로 표시한 캡처입니다. 실시간 터미널 화면이 아닙니다.</p>
<div class="meta">{html.escape(settings)}<br>Started: {result['started_at']} · observed {result['observation_seconds']:.3f}s<br>Launcher PID {result['launcher_pid']} · returncode {result['returncode']} · harness_stopped={str(result['harness_stopped']).lower()}</div>
{body}<footer>Source: evidence/{name}/ · 앱 로그 KST / 관제·시스템 로그 UTC · 앱 부하 표시와 OS CPU 측정은 별개입니다.</footer></main></html>'''
        page=page.replace('原文行番号 / ','')
        (DEST/f'{name}.html').write_text(page,encoding='utf-8')
        manifest.append(dict(name=name,width=1360,height=height))
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Created 6 saved-log viewer pages and screenshot dimensions.')
    return manifest

def capture(manifest):
    chrome=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chrome')
    if not chrome and os.name=='nt':
        candidate=Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe'
        if candidate.exists():
            chrome=str(candidate)
    if not chrome:
        raise SystemExit('Google Chrome or Chromium is required for PNG capture.')
    for item in manifest:
        output=DEST/f'{item["name"]}.png'
        command=[chrome,'--headless','--disable-gpu','--hide-scrollbars','--no-first-run','--no-default-browser-check',
                 f'--user-data-dir={ROOT / "tmp" / "render-profile"}',f'--screenshot={output}',
                 f'--window-size={item["width"]},{item["height"]}',(DEST/f'{item["name"]}.html').as_uri()]
        options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        subprocess.run(command,check=True,timeout=30,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**options)
        if not output.exists():
            raise RuntimeError(f'Capture missing: {output}')
        print(f'Captured: {item["name"]}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture',action='store_true',help='Render PNG screenshots using installed Chrome/Chromium.')
    args=parser.parse_args()
    manifest=build()
    if args.capture:
        capture(manifest)
