#!/usr/bin/env python3
"""Render this repository's small Markdown guide as an offline reading document."""
import html
import re
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/explanation-guide.md'

def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',r'<img src="\2" alt="\1">',text)
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',text)
    return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',text)

def build(source=SOURCE):
    source=Path(source)
    lines=source.read_text(encoding='utf-8').splitlines()
    title=lines[0][2:]
    intro=[]
    sections=[]
    nav=[]
    current=intro
    i=1
    while i<len(lines):
        line=lines[i]
        if not line.strip():
            i+=1
            continue
        if line.startswith('## '):
            heading=line[3:]
            section_id=f'chapter-{len(sections)+1}'
            current=[]
            sections.append((section_id,heading,current))
            if len(sections)<=6:
                nav.append((section_id,heading))
            i+=1
        elif line.startswith('### '):
            current.append(f'<h3>{inline(line[4:])}</h3>')
            i+=1
        elif line.startswith('```'):
            code=[]
            i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i+=1
            current.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
            i+=1
        elif line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                row=[cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',cell) for cell in row):
                    rows.append(row)
                i+=1
            header='<thead><tr>'+''.join(f'<th>{inline(c)}</th>' for c in rows[0])+'</tr></thead>'
            body='<tbody>'+''.join('<tr>'+''.join(f'<td>{inline(c)}</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody>'
            current.append('<div class="table-wrap"><table>'+header+body+'</table></div>')
        elif line.startswith('> '):
            current.append('<blockquote><span class="quote-label">이렇게 설명하세요</span><p>'+inline(line[2:])+'</p></blockquote>')
            i+=1
        else:
            paragraph=[]
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('## ','### ','```','|','> ')):
                paragraph.append(lines[i]); i+=1
            current.append('<p>'+inline(' '.join(paragraph))+'</p>')
    css='''
*{box-sizing:border-box}html{scroll-padding-top:120px}body{margin:0;background:#edf2f7;color:#20334b;font-family:"Malgun Gothic",Arial,sans-serif;font-size:16px;line-height:1.85;word-break:keep-all}a{color:#1266a8;text-underline-offset:3px}nav{position:sticky;top:0;z-index:5;background:#102840;padding:12px 24px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap;box-shadow:0 2px 8px #1028401a}nav a{color:#e5eff7;font-size:13px;padding:3px 11px;border:1px solid #3b526b;border-radius:20px;text-decoration:none}nav a:hover{background:#31536f}.wrap{max-width:1040px;margin:auto;padding:34px 32px 64px}.hero{padding:10px 6px 24px}.eyebrow{font-size:12px;letter-spacing:1.5px;color:#38678d;font-weight:700}h1{font-size:34px;line-height:1.35;letter-spacing:-1.3px;margin:14px 0 22px;color:#102840}h2{font-size:25px;line-height:1.5;margin:0 0 22px;letter-spacing:-.6px;color:#102840;border-bottom:2px solid #dce7ef;padding-bottom:15px}h3{font-size:18px;color:#155780;margin:28px 0 8px}p{margin:13px 0}strong{font-weight:700;color:#132c47}.chapter{background:white;border:1px solid #dae4ec;border-radius:16px;padding:32px 36px;margin:0 0 24px;box-shadow:0 4px 20px #18334d04}.table-wrap{overflow-x:auto;margin:22px 0}table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:14px;line-height:1.7}th,td{text-align:left;padding:12px 13px;border-bottom:1px solid #dfe8ef;vertical-align:top;word-break:keep-all;overflow-wrap:anywhere}th{background:#edf4f8;color:#1b4d71;font-weight:700}th:first-child{width:16%}tr:last-child td{border-bottom:0}td:first-child{font-weight:600}blockquote{margin:26px 0 0;background:#edf6fc;border-left:4px solid #2d83b7;border-radius:0 10px 10px 0;padding:18px 22px;color:#1f4866}.quote-label{font-weight:700;font-size:12px;color:#246788}blockquote p{margin:7px 0 0}pre{background:#12283e;color:#dcebf8;padding:19px 22px;border-radius:10px;overflow-wrap:anywhere;white-space:pre-wrap;font:14px/1.8 Consolas,monospace;word-break:break-word}code{font:0.89em Consolas,monospace;background:#edf2f6;border-radius:4px;padding:2px 4px;overflow-wrap:anywhere}pre code{background:none;padding:0;font:inherit}img{display:block;width:100%;height:auto;border-radius:10px;margin:20px 0;border:1px solid #e2e9ef}.footer{text-align:center;color:#6c7e8e;font-size:13px;margin-top:26px}.toplink{font-size:13px;margin-top:22px;display:block}@media(max-width:700px){.wrap{padding:22px 14px}.chapter{padding:24px 20px}h1{font-size:28px}h2{font-size:22px}nav{position:static;justify-content:flex-start;padding:12px}body{font-size:15px}table{min-width:530px}}@media print{body{background:white;font-size:11pt}nav,.toplink{display:none}.wrap{padding:0;max-width:none}.hero{padding:0 0 12px}.chapter{box-shadow:none;border:0;border-radius:0;margin:0;padding:20px 0;break-before:page}h2,h3{break-after:avoid}img,table,blockquote,pre{break-inside:avoid}.table-wrap{overflow:visible}a{color:inherit;text-decoration:none}h1{font-size:26pt}h2{font-size:20pt}img{max-height:90mm;object-fit:contain}table{font-size:10pt}footer{display:none}}
'''
    navigation=''.join(f'<a href="#{sid}">{html.escape(heading)}</a>' for sid,heading in nav)
    body=''.join(f'<section class="chapter" id="{sid}"><h2>{html.escape(heading)}</h2>'+''.join(parts)+'<a class="toplink" href="#top">맨 위로</a></section>' for sid,heading,parts in sections)
    output=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><style>{css}</style></head><body id="top"><nav aria-label="문서 목차">{navigation}</nav><main class="wrap"><header class="hero"><div class="eyebrow">LINUX 장애 분석 · 설명과 발표 가이드</div><h1>{html.escape(title)}</h1>{''.join(intro)}</header>{body}<footer class="footer">실험일 2026.10.20 · 보너스 제외 · 실제 로그와 관제 자료에 근거한 설명</footer></main></body></html>'''
    destination=source.with_suffix('.html')
    destination.write_text(output,encoding='utf-8')
    print(f'Rendered {destination.name} from {source.name}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',nargs='?',type=Path,default=SOURCE)
    args=parser.parse_args()
    build(args.source)
