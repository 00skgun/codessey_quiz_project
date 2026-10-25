"""Render the reviewed local study data into PDF, offline HTML and Markdown."""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Preformatted

DATA = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
OUT = ROOT.parent / "pdf"
OUT.mkdir(parents=True, exist_ok=True)
QA = ROOT.parent / "study-qa"
QA.mkdir(parents=True, exist_ok=True)
FONT = "Malgun"
BOLD = "MalgunBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))
pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=BOLD, italic=FONT, boldItalic=BOLD)
INK = colors.HexColor("#182C3B")
MUTED = colors.HexColor("#506372")
ACCENT = colors.HexColor("#087D83")
PALE = colors.HexColor("#EAF6F5")
LINE = colors.HexColor("#D8E3E8")
WIDTH, HEIGHT = 595.276, 841.89
LEFT, RIGHT = 47, 47
CW = WIDTH - LEFT - RIGHT


def esc(value):
    return html.escape(str(value), quote=False)


def sty(kind="body", scale=1):
    base = dict(fontName=FONT, fontSize=10.2 * scale, leading=16.3 * scale,
                textColor=INK, wordWrap="CJK", alignment=TA_LEFT, spaceAfter=0)
    if kind == "small":
        base.update(fontSize=8.3 * scale, leading=12.8 * scale, textColor=MUTED)
    elif kind == "cell":
        base.update(fontSize=9.2 * scale, leading=13.5 * scale)
    elif kind == "th":
        base.update(fontName=BOLD, fontSize=9 * scale, leading=13.5 * scale,
                    textColor=colors.white)
    elif kind == "heading":
        base.update(fontName=BOLD, fontSize=12 * scale, leading=18 * scale,
                    textColor=ACCENT)
    elif kind == "lead":
        base.update(fontName=BOLD, fontSize=17.2 * scale, leading=26 * scale,
                    textColor=ACCENT)
    elif kind == "code":
        base.update(fontSize=8.5 * scale, leading=12.3 * scale)
    return ParagraphStyle(kind, **base)


def para(text, kind="body", scale=1):
    return Paragraph(esc(text).replace("\n", "<br/>"), sty(kind, scale))


def panel(text, label=None, scale=1, quote=False):
    content = []
    if label:
        content.extend([para(label, "heading", scale), Spacer(1, 4 * scale)])
    content.append(para(text, scale=scale))
    tab = Table([[content]], colWidths=[CW])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 13 * scale),
        ("RIGHTPADDING", (0, 0), (-1, -1), 13 * scale),
        ("TOPPADDING", (0, 0), (-1, -1), 9 * scale),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9 * scale),
    ]))
    return tab


def table(block, scale):
    n = len(block["headers"])
    widths = [CW * x for x in ([.29, .39, .32] if n == 3 else [.34, .66])]
    if block["headers"][0].startswith("가상"):
        widths = [CW * .34, CW * .33, CW * .33]
    if block["headers"][0] == "이슈 / PR":
        widths = [CW * .25, CW * .61, CW * .14]
    data = [[para(x, "th", scale) for x in block["headers"]]]
    data.extend([[para(x, "cell", scale) for x in row] for row in block["rows"]])
    tab = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * scale),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8 * scale),
        ("TOPPADDING", (0, 0), (-1, -1), 6 * scale),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6 * scale),
        ("LINEBELOW", (0, 1), (-1, -1), .45, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
    ]))
    return tab


def flowables(page, scale):
    result = []
    for block in page["blocks"]:
        kind = block["type"]
        if kind in ("p", "lead", "heading"):
            result.append(para(block["text"], {"p":"body"}.get(kind, kind), scale))
        elif kind in ("quote", "callout"):
            result.append(panel(block["text"], block.get("label"), scale))
        elif kind == "table":
            result.append(table(block, scale))
        elif kind in ("steps", "bullets"):
            for idx, item in enumerate(block["items"], 1):
                prefix = f"{idx:02d}. " if kind == "steps" else "• "
                result.append(para(prefix + item, scale=scale))
                result.append(Spacer(1, 5 * scale))
        elif kind == "code":
            wrapped = []
            fs = sty("code", scale).fontSize
            for line in block["text"].splitlines():
                if pdfmetrics.stringWidth(line, FONT, fs) > CW - 22:
                    raise ValueError(f"Code line too wide: {page['id']}: {line}")
                wrapped.append(line)
            pre = Preformatted("\n".join(wrapped), sty("code", scale))
            tab = Table([[pre]], colWidths=[CW])
            tab.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F0F4F7")),
                ("LEFTPADDING",(0,0),(-1,-1),11),
                ("RIGHTPADDING",(0,0),(-1,-1),11),
                ("TOPPADDING",(0,0),(-1,-1),9 * scale),
                ("BOTTOMPADDING",(0,0),(-1,-1),9 * scale),
            ]))
            result.append(tab)
        elif kind == "quiz":
            result.extend([para(block["q"], "heading", scale), Spacer(1, 3 * scale),
                           para(block["a"], scale=scale)])
        elif kind == "links":
            for label, url in block["items"]:
                result.append(Paragraph(
                    f'<link href="{html.escape(url, quote=True)}" color="#087D83">{esc(label)}</link>',
                    sty("cell", scale)))
                result.append(Spacer(1, 3 * scale))
        else:
            raise ValueError(kind)
        result.append(Spacer(1, 10 * scale if kind != "heading" else 5 * scale))
    return result


def make_pdf():
    path = OUT / "geonyoung-db-study-guide.pdf"
    c = canvas.Canvas(str(path), pagesize=(WIDTH, HEIGHT), pageCompression=1)
    c.setTitle(DATA["title"])
    c.setAuthor("최건영 / DB·로그 담당 C")
    diagnostics = []
    for idx, page in enumerate(DATA["pages"], 1):
        top = HEIGHT - 127
        room = top - 57
        selected = None
        for scale in (1, .98, .96, .94, .92, .90):
            flows = flowables(page, scale)
            sizes = [f.wrap(CW, HEIGHT) for f in flows]
            total = sum(h for w, h in sizes)
            if total <= room:
                selected = (scale, flows, sizes, total)
                break
        if selected is None:
            raise ValueError(f"Page {idx} overflows: {total:.1f} > {room:.1f}")
        scale, flows, sizes, total = selected
        c.bookmarkPage(page["id"])
        c.addOutlineEntry(f"{idx:02d}. {page['title']}", page["id"], 0, False)
        c.setFillColor(ACCENT)
        c.rect(0, HEIGHT - 8, WIDTH, 8, fill=1, stroke=0)
        c.setFont(BOLD, 8)
        c.drawString(LEFT, HEIGHT - 36, "B7-1  /  DATABASE & LOGS  /  STUDY GUIDE")
        c.setFillColor(MUTED)
        c.setFont(FONT, 8)
        c.drawRightString(WIDTH - RIGHT, HEIGHT - 36, DATA["date"])
        c.setFillColor(ACCENT)
        c.setFont(BOLD, 8.5)
        c.drawString(LEFT, HEIGHT - 62, page["tag"])
        title = para(page["title"], "lead")
        tw, th = title.wrap(CW, 52)
        title.drawOn(c, LEFT, HEIGHT - 72 - th)
        if th > 45:
            raise ValueError("Title wraps too far: " + page["title"])
        y = top
        for f, (w, h) in zip(flows, sizes):
            y -= h
            f.drawOn(c, LEFT, y)
        c.setStrokeColor(LINE)
        c.line(LEFT, 43, WIDTH - RIGHT, 43)
        c.setFont(FONT, 7.7)
        c.setFillColor(MUTED)
        c.drawString(LEFT, 28, "최건영 · 00skgun  |  코드 근거 → 구현 이유 → 검증")
        c.drawRightString(WIDTH - RIGHT, 28, f"{idx:02d} / {len(DATA['pages']):02d}")
        diagnostics.append({"page":idx, "id":page["id"], "scale":scale,
                            "content_height":round(total, 2), "bottom":round(y, 2)})
        c.showPage()
    c.save()
    (QA / "layout.json").write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def html_block(block):
    t = block["type"]
    if t in ("p", "lead"):
        return f'<p class="{t}">{esc(block["text"])}</p>'
    if t == "heading":
        return f'<h3>{esc(block["text"])}</h3>'
    if t in ("quote", "callout"):
        label = f'<strong>{esc(block["label"])}</strong>' if "label" in block else ""
        return f'<aside class="callout">{label}<p>{esc(block["text"])}</p></aside>'
    if t == "table":
        heads = "".join(f"<th>{esc(x)}</th>" for x in block["headers"])
        rows = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in block["rows"])
        return f'<div class="table-wrap"><table><thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table></div>'
    if t == "code":
        return f'<pre><code>{esc(block["text"])}</code></pre>'
    if t in ("steps", "bullets"):
        tag = "ol" if t == "steps" else "ul"
        return f'<{tag} class="{t}">' + "".join(f"<li>{esc(x)}</li>" for x in block["items"]) + f'</{tag}>'
    if t == "quiz":
        return f'<details class="quiz"><summary>{esc(block["q"])}</summary><p>{esc(block["a"])}</p></details>'
    if t == "links":
        return '<ul class="links">' + "".join(f'<li><a href="{html.escape(url,quote=True)}" target="_blank" rel="noreferrer">{esc(label)}</a></li>' for label, url in block["items"]) + '</ul>'
    raise ValueError(t)


def make_html():
    nav = "".join(f'<a href="#{page["id"]}"><span>{idx:02d}</span>{esc(page["title"])}</a>' for idx, page in enumerate(DATA["pages"], 1))
    sections = "".join(f'<section id="{page["id"]}"><div class="eyebrow">{esc(page["tag"])}</div><h2><span>{idx:02d}</span>{esc(page["title"])}</h2>' + "".join(html_block(b) for b in page["blocks"]) + '</section>' for idx, page in enumerate(DATA["pages"],1))
    css = """
    :root{color-scheme:light;--ink:#182c3b;--muted:#506372;--teal:#087d83;--pale:#eaf6f5;--line:#d8e3e8}
    *{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:20px}body{margin:0;background:#edf2f5;color:var(--ink);font:16px/1.85 'Malgun Gothic','Apple SD Gothic Neo',sans-serif;word-break:keep-all;overflow-wrap:anywhere}
    .hero{background:var(--ink);color:#fff;padding:48px max(28px,calc((100vw - 1180px)/2));border-top:7px solid #24b6ac}.hero h1{font-size:clamp(26px,3.5vw,42px);line-height:1.35;margin:10px 0}.hero p{color:#d7e7ed;margin:8px 0}.hero .label{font:12px/1.5 sans-serif;letter-spacing:2px;color:#8ad9d2}.hero .meta{font-size:13px;color:#b8cbd3}
    .shell{max-width:1240px;margin:0 auto;display:grid;grid-template-columns:265px minmax(0,1fr);gap:28px;padding:28px}.navbox{position:sticky;top:18px;align-self:start;background:#fff;padding:20px;border:1px solid var(--line);border-radius:12px;max-height:calc(100vh - 36px);overflow:auto}.navbox h2{font-size:15px;margin:0 0 12px}.navbox a{display:block;color:var(--muted);text-decoration:none;font-size:13px;line-height:1.5;padding:8px 0}.navbox a:hover{color:var(--teal)}.navbox span{display:inline-block;width:26px;color:var(--teal);font-weight:700}.tools{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 0}button,.pdf-link{border:1px solid var(--line);border-radius:7px;padding:9px 12px;background:#fff;color:var(--ink);font:inherit;font-size:13px;cursor:pointer;text-decoration:none}button:hover,.pdf-link:hover{background:var(--pale)}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #d39030;outline-offset:3px}
    main{min-width:0}section{background:white;border:1px solid var(--line);border-radius:14px;padding:32px 36px;margin-bottom:24px;scroll-margin-top:20px}.eyebrow{font-size:11px;letter-spacing:1px;font-weight:bold;color:var(--teal)}h2{font-size:25px;line-height:1.5;margin:8px 0 22px}h2 span{font-size:17px;color:var(--teal);display:block}h3{font-size:18px;color:var(--teal);margin:25px 0 10px}p{margin:12px 0}.lead{font-size:21px;font-weight:700;line-height:1.65;color:var(--teal)}.callout{background:var(--pale);border-left:4px solid var(--teal);padding:16px 20px;margin:22px 0;border-radius:0 7px 7px 0}.callout p{margin:6px 0 0}.callout strong{color:var(--teal)}.table-wrap{overflow-x:auto;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.65}th,td{text-align:left;vertical-align:top;padding:11px 12px;border-bottom:1px solid var(--line)}th{background:var(--ink);color:white;font-weight:600}tr:nth-child(even) td{background:#f5f8fa}pre{background:#f0f4f7;border:1px solid #e0e8ed;border-radius:7px;padding:18px;font-size:13px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere;tab-size:4}code{font-family:Consolas,'Malgun Gothic',monospace}.steps{padding-left:28px}.steps li{padding:5px 0 10px 7px}.steps li::marker{font-weight:700;color:var(--teal)}li{margin:7px 0}.quiz{border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:14px 17px}.quiz summary{cursor:pointer;font-weight:700;line-height:1.7}.quiz[open]{background:var(--pale)}.quiz p{padding-top:8px;border-top:1px solid #badedb}.links a{color:var(--teal)}footer{color:var(--muted);font-size:13px;text-align:center;padding:15px 0 30px}
    @media(max-width:900px){.shell{grid-template-columns:1fr;padding:18px;gap:18px}.navbox{position:static;max-height:none}.navbox nav{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}section{padding:25px}h2{font-size:22px}}
    @media(max-width:480px){.hero{padding:30px 20px}.shell{padding:12px}.navbox nav{grid-template-columns:1fr}section{padding:20px 17px}.table-wrap{font-size:13px}th,td{padding:8px}.lead{font-size:19px}pre{font-size:12px;padding:12px}h2{font-size:21px}}
    @media print{body{background:white;font-size:10pt}.hero,.navbox,.tools,footer{display:none}.shell{display:block;padding:0}section{border:0;border-radius:0;padding:0;page-break-after:always}section:last-child{page-break-after:auto}h2{font-size:18pt}h3{font-size:12pt}table{font-size:9pt}pre{font-size:8.5pt}.quiz{break-inside:avoid}.callout{break-inside:avoid}a{color:inherit}.lead{font-size:14pt}@page{size:A4;margin:18mm}}
    """
    js = """
    const answers = [...document.querySelectorAll('details.quiz')];
    document.getElementById('reveal').addEventListener('click',()=>answers.forEach(x=>x.open=true));
    document.getElementById('conceal').addEventListener('click',()=>answers.forEach(x=>x.open=false));
    window.addEventListener('beforeprint',()=>answers.forEach(x=>x.open=true));
    """
    document = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(DATA['title'])}</title><style>{css}</style></head><body>
    <header class="hero"><div class="label">B7-1 · PERSONAL STUDY EDITION</div><h1>내가 만든 DB,<br>내 말로 설명하기</h1><p>{esc(DATA['subtitle'])}</p><p class="meta">{DATA['date']} 기준 · 18개 주제 · 예상 질문 18개 + 손풀이 1개 · 인터넷 없이 학습 가능</p><div class="tools"><a class="pdf-link" href="geonyoung-db-study-guide.pdf">인쇄용 PDF 열기</a><button id="reveal" type="button">모든 정답 펼치기</button><button id="conceal" type="button">정답 가리기</button></div></header>
    <div class="shell"><aside class="navbox"><h2>학습 목차</h2><nav aria-label="학습 목차">{nav}</nav></aside><main>{sections}<footer>개인 학습용 · 실제 비밀값 없음 · 앱 코드와 Git 이력은 변경하지 않음</footer></main></div><script>{js}</script></body></html>'''
    path = OUT / "geonyoung-db-study-guide.html"
    path.write_text(document, encoding="utf-8")
    return path


def make_markdown():
    lines = ["# " + DATA["title"], "", DATA["subtitle"], "", DATA["date"] + " 기준", ""]
    for idx, page in enumerate(DATA["pages"], 1):
        lines.extend([f"## {idx:02d}. {page['title']}", ""])
        for b in page["blocks"]:
            t = b["type"]
            if t in ("p", "lead"):
                lines.append(b["text"])
            elif t == "heading":
                lines.append("### " + b["text"])
            elif t in ("callout", "quote"):
                lines.append("> " + (b.get("label", "") + ": " if "label" in b else "") + b["text"])
            elif t == "code":
                lines.extend(["```", b["text"], "```"])
            elif t in ("steps", "bullets"):
                lines.extend([(f"{i}. " if t == "steps" else "- ") + x for i,x in enumerate(b["items"],1)])
            elif t == "table":
                lines.extend(["| " + " | ".join(b["headers"]) + " |", "| " + " | ".join(["---"]*len(b["headers"])) + " |"])
                lines.extend(["| " + " | ".join(row) + " |" for row in b["rows"]])
            elif t == "quiz":
                lines.extend(["<details>", "<summary>" + b["q"] + "</summary>", "", b["a"], "", "</details>"])
            elif t == "links":
                lines.extend([f"- [{label}]({url})" for label,url in b["items"]])
            lines.append("")
    path = OUT / "geonyoung-db-study-guide.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


if __name__ == "__main__":
    for builder in (make_pdf, make_html, make_markdown):
        print(builder())
