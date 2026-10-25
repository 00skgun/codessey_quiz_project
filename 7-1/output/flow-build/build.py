"""Build private learning artifacts. Does not import or change the app."""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'study-build' / 'vendor'))
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Preformatted

DATA = json.loads((ROOT / 'content.json').read_text(encoding='utf-8'))
OUT = ROOT.parent / 'pdf'
QA = ROOT.parent / 'flow-qa'
OUT.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)
STEM = 'chatbot-program-flow-geonyoung'
FONT, BOLD = 'FlowMalgun', 'FlowMalgunBold'
pdfmetrics.registerFont(TTFont(FONT, 'C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont(BOLD, 'C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=BOLD, italic=FONT, boldItalic=BOLD)
W, H, M = 595.276, 841.89, 42
CW = W - M * 2
INK, MUTED, TEAL = map(colors.HexColor, ['#173441', '#506873', '#06776E'])
LINE, PALE, GRAY = map(colors.HexColor, ['#D4E1E4', '#E7F5F1', '#F3F6F7'])


def esc(text):
    return html.escape(str(text), quote=False)


def style(kind='body', scale=1):
    size, leading, bold, color = {
        'body': (10.5, 16.1, False, INK),
        'cell': (9.6, 14.3, False, INK),
        'small': (9.2, 14, False, MUTED),
        'heading': (12, 18, True, TEAL),
        'lead': (16, 23, True, TEAL),
        'th': (9.3, 14, True, colors.white),
        'code': (9.4, 14, False, INK),
        'ref': (7.5, 11, False, MUTED),
    }[kind]
    return ParagraphStyle(kind, fontName=BOLD if bold else FONT,
                          fontSize=size*scale, leading=leading*scale,
                          textColor=color, wordWrap='CJK', splitLongWords=True)


def para(text, kind='body', scale=1, raw=False):
    return Paragraph(text if raw else esc(text).replace('\n', '<br/>'), style(kind, scale))


def box(text, label, scale=1, mine=False):
    p = para(f'<b>{esc(label)}</b><br/>{esc(text)}', scale=scale, raw=True)
    t = Table([[p]], colWidths=[CW])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), PALE if mine else GRAY),
        ('LINEBEFORE',(0,0),(0,-1),3,TEAL if mine else LINE),
        ('LEFTPADDING',(0,0),(-1,-1),12), ('RIGHTPADDING',(0,0),(-1,-1),12),
        ('TOPPADDING',(0,0),(-1,-1),8*scale), ('BOTTOMPADDING',(0,0),(-1,-1),8*scale),
    ]))
    return t


def make_table(b, scale):
    widths = [CW*x for x in b['widths']]
    data = [[para(v, 'th', scale) for v in b['headers']]]
    data += [[para(v, 'cell', scale) for v in row] for row in b['rows']]
    t = Table(data, colWidths=widths, hAlign='LEFT')
    commands = [
        ('BACKGROUND',(0,0),(-1,0),INK), ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8), ('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),6*scale), ('BOTTOMPADDING',(0,0),(-1,-1),6*scale),
        ('LINEBELOW',(0,1),(-1,-1),.4,LINE),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,GRAY]),
    ]
    for idx, heading in enumerate(b['headers']):
        if heading.startswith('C ·'):
            commands.append(('BACKGROUND',(idx,1),(idx,-1),PALE))
    t.setStyle(TableStyle(commands))
    return t


def make_steps(items, scale):
    rows=[]
    for i,(owner, title, body) in enumerate(items,1):
        mine=owner=='C' or 'C' in owner
        marker = f'<b>{i:02d}</b><br/>{esc(owner)}'
        content=f'<b>{esc(title)}</b><br/>{esc(body)}'
        rows.append([para(marker,'cell',scale,raw=True),para(content,'body',scale,raw=True)])
    t=Table(rows,colWidths=[62,CW-62])
    commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),
              ('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),6*scale),
              ('BOTTOMPADDING',(0,0),(-1,-1),7*scale),('LINEBELOW',(0,0),(-1,-1),.5,LINE)]
    for i,item in enumerate(items):
        if 'C' in item[0]: commands.append(('BACKGROUND',(0,i),(-1,i),PALE))
    t.setStyle(TableStyle(commands))
    return t


def flows(page, scale):
    result=[]
    for b in page['blocks']:
        kind=b['type']
        if kind in ('p','heading','lead'):
            result.append(para(b['text'], 'body' if kind=='p' else kind, scale))
        elif kind in ('mine','note','quote'):
            result.append(box(b['text'], {'mine':'C · 내가 구현','note':'구분해서 기억하기','quote':'평가 답변 예시'}[kind], scale, kind=='mine'))
        elif kind=='table': result.append(make_table(b,scale))
        elif kind=='steps': result.append(make_steps(b['items'],scale))
        elif kind=='code':
            for line in b['text'].splitlines():
                if pdfmetrics.stringWidth(line,FONT,style('code',scale).fontSize)>CW-22:
                    raise ValueError('Code too wide: '+line)
            t=Table([[Preformatted(b['text'],style('code',scale))]],colWidths=[CW])
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRAY),
                ('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),
                ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
            result.append(t)
        elif kind=='quiz':
            result.extend([para('확인 질문 · '+b['q'],'heading',scale),Spacer(1,4*scale),para(b['a'],'body',scale)])
        else: raise ValueError(kind)
        result.append(Spacer(1,8*scale))
    return result


def source_url(path):
    if path.startswith('https://'): return path
    return f'https://github.com/Teamb7-1/ai-chatbot-service/blob/{DATA["ref"]}/{path}'


def make_pdf():
    path=OUT / (STEM+'.pdf')
    c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1)
    c.setTitle(DATA['title']);c.setAuthor('최건영 / 개인 학습 자료')
    diagnostics=[]
    for idx,p in enumerate(DATA['pages'],1):
        top=H-116; room=top-98
        selected=None
        for scale in (1,.98,.96,.94,.92):
            fs=flows(p,scale); sizes=[f.wrap(CW,H) for f in fs]
            total=sum(x[1] for x in sizes)
            if total<=room: selected=scale,fs,sizes,total;break
        if selected is None: raise ValueError(f'Page {idx} overflow {total:.1f}/{room:.1f}; shorten content')
        scale,fs,sizes,total=selected
        c.bookmarkPage(p['id']);c.addOutlineEntry(f'{idx:02d}. {p["title"]}',p['id'],0,False)
        c.setFillColor(TEAL);c.rect(0,H-6,W,6,stroke=0,fill=1)
        c.setFont(BOLD,8);c.drawString(M,H-30,'B7-1 / PROGRAM FLOW / PERSONAL STUDY')
        c.setFillColor(MUTED);c.setFont(FONT,8);c.drawRightString(W-M,H-30,DATA['date'])
        c.setFillColor(TEAL);c.setFont(BOLD,8.5);c.drawString(M,H-54,p['tag'])
        title=Paragraph(esc(p['title']),ParagraphStyle('title',fontName=BOLD,fontSize=22,leading=30,textColor=INK,wordWrap='CJK'))
        tw,th=title.wrap(CW,60)
        if th>35: raise ValueError('Title too long '+p['title'])
        title.drawOn(c,M,H-66-th)
        y=top
        for f,(_,h) in zip(fs,sizes): y-=h;f.drawOn(c,M,y)
        refs=[]
        for label,target in p['refs']:
            refs.append(f'<link href="{html.escape(source_url(target),quote=True)}" color="#06776E">{esc(label)}</link>')
        reference=para('코드·자료 근거: '+'  /  '.join(refs),'ref',raw=True)
        _,rh=reference.wrap(CW,40);reference.drawOn(c,M,57)
        if rh>29: raise ValueError('References too tall')
        c.setStrokeColor(LINE);c.line(M,44,W-M,44)
        c.setFont(FONT,7.6);c.setFillColor(MUTED)
        c.drawString(M,29,'최건영 · 00skgun | C 표시 = 내가 구현 | 기준 b1cca1e')
        c.drawRightString(W-M,29,f'{idx:02d} / {len(DATA["pages"]):02d}')
        diagnostics.append({'page':idx,'scale':scale,'height':round(total,1),'bottom':round(y,1)})
        c.showPage()
    c.save()
    (QA/'layout.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    return path


def html_block(b):
    kind=b['type']
    if kind in ('p','lead'): return f'<p class="{kind}">{esc(b["text"])}</p>'
    if kind=='heading': return f'<h3>{esc(b["text"])}</h3>'
    if kind in ('mine','note','quote'):
        label={'mine':'C · 내가 구현','note':'구분해서 기억하기','quote':'평가 답변 예시'}[kind]
        return f'<aside class="{kind}"><strong>{label}</strong><p>{esc(b["text"])}</p></aside>'
    if kind=='steps':
        rows=''
        for i,(owner,title,body) in enumerate(b['items'],1):
            flag=' own' if 'C' in owner else ''
            rows+=f'<li class="step{flag}"><div class="stepmark"><b>{i:02d}</b><span>{esc(owner)}</span></div><div><h4>{esc(title)}</h4><p>{esc(body)}</p></div></li>'
        return '<ol class="steps">'+rows+'</ol>'
    if kind=='table':
        head=''.join(f'<th scope="col">{esc(x)}</th>' for x in b['headers'])
        body=''
        for row in b['rows']:
            body+='<tr>'+''.join(f'<td{chr(32)+"class=own" if b["headers"][i].startswith("C ·") else ""}>{esc(x)}</td>' for i,x in enumerate(row))+'</tr>'
        return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    if kind=='code': return f'<pre><code>{esc(b["text"])}</code></pre>'
    if kind=='quiz': return f'<details><summary>{esc(b["q"])}</summary><p>{esc(b["a"])}</p></details>'
    raise ValueError(kind)


def make_html():
    sections=[];nav=[]
    for idx,p in enumerate(DATA['pages'],1):
        nav.append(f'<a href="#{p["id"]}"><span>{idx:02d}</span> {esc(p["title"])}</a>')
        refs=' · '.join(f'<a href="{html.escape(source_url(target),quote=True)}" target="_blank" rel="noreferrer">{esc(label)}</a>' for label,target in p['refs'])
        sections.append(f'<section id="{p["id"]}"><p class="eyebrow">{esc(p["tag"])}</p><h2>{esc(p["title"])}</h2>'+''.join(html_block(b) for b in p['blocks'])+f'<p class="refs">코드·자료 근거: {refs}</p></section>')
    template=(ROOT/'template.html').read_text(encoding='utf-8')
    rendered=template.replace('%%TITLE%%',esc(DATA['title'])).replace('%%SUBTITLE%%',esc(DATA['subtitle'])).replace('%%NAV%%',''.join(nav)).replace('%%SECTIONS%%',''.join(sections)).replace('%%PDF%%',STEM+'.pdf')
    path=OUT/(STEM+'.html');path.write_text(rendered,encoding='utf-8');return path


def make_md():
    lines=['# '+DATA['title'],'',DATA['subtitle'],'',f'{DATA["date"]} / 코드 기준 {DATA["ref"]}','']
    for idx,p in enumerate(DATA['pages'],1):
        lines.extend([f'## {idx:02d}. {p["title"]}',''])
        for b in p['blocks']:
            k=b['type']
            if k in ('p','lead'):lines.append(b['text'])
            elif k=='heading':lines.append('### '+b['text'])
            elif k in ('mine','quote','note'):lines.append('> '+({'mine':'C · 내가 구현: ','quote':'평가 답변: ','note':'기억할 점: '}[k])+b['text'])
            elif k=='code':lines.extend(['```python',b['text'],'```'])
            elif k=='steps':lines.extend(f'{i}. **[{owner}] {title}**: {body}' for i,(owner,title,body) in enumerate(b['items'],1))
            elif k=='table':
                lines.extend(['| '+' | '.join(b['headers'])+' |','| '+' | '.join(['---']*len(b['headers']))+' |'])
                lines.extend('| '+' | '.join(row)+' |' for row in b['rows'])
            elif k=='quiz':lines.extend(['**확인 질문: '+b['q']+'**','',b['a']])
            lines.append('')
        lines.append('근거: '+' / '.join(f'[{label}]({source_url(target)})' for label,target in p['refs']));lines.append('')
    path=OUT/(STEM+'.md');path.write_text('\n'.join(lines),encoding='utf-8');return path


if __name__=='__main__':
    for fn in (make_pdf,make_html,make_md):print(fn())
