"""Render and inspect private PDF/HTML without running app code or database calls."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'study-build'/'vendor'))
import pymupdf
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont

OUT=ROOT.parent/'pdf';QA=ROOT.parent/'flow-qa';QA.mkdir(exist_ok=True)
STEM='chatbot-program-flow-geonyoung'
data=json.loads((ROOT/'content.json').read_text(encoding='utf-8'))
count=len(data['pages'])
pdf=OUT/(STEM+'.pdf');reader=PdfReader(pdf)
assert len(reader.pages)==len(reader.outline)==count==12
doc=pymupdf.open(pdf)
issues=[]
for idx,(page,source) in enumerate(zip(doc,data['pages']),1):
    text=page.get_text()
    assert source['title'] in text.replace('\n',' '),(idx,'missing title')
    assert '\ufffd' not in text,(idx,'replacement characters')
    assert f'{idx:02d} / {count:02d}' in text,(idx,'missing page number')
    assert len(page.get_links())==len(source['refs']),(idx,'source links')
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            x0,y0,x1,y1=line['bbox']
            if x0<38 or x1>557 or y0<12 or y1>824:
                issues.append({'page':idx,'bbox':line['bbox'],'text':''.join(s['text'] for s in line['spans'])})
    page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(QA/f'page-{idx:02d}.png')
assert not issues,issues
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',20)
for first in range(0,count,4):
    sheet=Image.new('RGB',(1200,1700),'#dfe8eb');draw=ImageDraw.Draw(sheet)
    for offset in range(min(4,count-first)):
        n=first+offset+1;tile=Image.open(QA/f'page-{n:02d}.png');tile.thumbnail((570,807))
        x=(offset%2)*600+15;y=(offset//2)*850+34
        draw.text((x,y-29),f'Page {n:02d}',font=font,fill='#173441');sheet.paste(tile,(x,y))
    sheet.save(QA/f'contact-{first//4+1}.png')

html=(OUT/(STEM+'.html')).read_text(encoding='utf-8')
assert '%%' not in html
assert not re.search(r'postgres(?:ql)?(?:\+psycopg)?://',html)
assert '<script src=' not in html
result={'pages':count,'outline':len(reader.outline),'out_of_bounds':issues,'html':{}}

if '--browser' in sys.argv:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1366,'height':1000},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.goto((OUT/(STEM+'.html')).as_uri())
        assert page.locator('main section').count()==12
        questions=sum(b['type']=='quiz' for x in data['pages'] for b in x['blocks'])
        assert page.locator('details').count()==questions==9
        assert page.locator('details[open]').count()==0
        page.locator('#reveal').click();assert page.locator('details[open]').count()==questions
        page.locator('#conceal').click();assert page.locator('details[open]').count()==0
        page.locator('#identity summary').click();assert page.locator('#identity details[open]').count()==1
        page.locator('#identity summary').click()
        page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(QA/'html-desktop.png'))
        for width in [390,320]:
            page.set_viewport_size({'width':width,'height':844})
            for target in ['overview','chat','history','recap']:
                page.locator('#'+target).scroll_into_view_if_needed()
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),(width,target,'document overflow')
                page.locator('#'+target).screenshot(path=str(QA/f'html-{width}-{target}.png'))
            result['html'][str(width)]='No document overflow'
        assert not errors,errors
        browser.close()
    result['html'].update({'questions':questions,'toggle_tests':'pass','javascript_errors':errors})
(QA/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
