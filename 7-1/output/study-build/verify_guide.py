"""Visual rendering plus structural checks of the final PDF and HTML."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))
import fitz
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

OUT = ROOT.parent / "pdf"
QA = ROOT.parent / "study-qa"
QA.mkdir(exist_ok=True)
source = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
pdf_path = OUT / "geonyoung-db-study-guide.pdf"
reader = PdfReader(pdf_path)
assert len(reader.pages) == len(source["pages"]) == 18
assert len(reader.outline) == 18
doc = fitz.open(pdf_path)
issues = []
for idx, (page, content) in enumerate(zip(doc, source["pages"]), 1):
    text = page.get_text()
    assert content["title"] in text.replace("\n", " "), (idx, "missing title")
    assert "\ufffd" not in text, (idx, "replacement character")
    assert f"{idx:02d} / 18" in text, (idx, "missing page number")
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            x0,y0,x1,y1 = line["bbox"]
            if x0 < 40 or x1 > 555.5 or y0 < 14 or y1 > 823:
                issues.append({"page":idx,"bbox":line["bbox"],
                               "text":"".join(s["text"] for s in line["spans"])})
    page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(QA / f"page-{idx:02d}.png")
assert not issues, issues
font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf",16)
for first in range(0,18,6):
    sheet = Image.new("RGB",(1200,1190),"#dfe7eb")
    draw = ImageDraw.Draw(sheet)
    for offset in range(6):
        number = first+offset+1
        tile = Image.open(QA / f"page-{number:02d}.png")
        tile.thumbnail((378,535))
        x = (offset%3)*400 + 11
        y = (offset//3)*590 + 33
        draw.text((x,y-25),f"{number:02d}",font=font,fill="#182c3b")
        sheet.paste(tile,(x,y))
    sheet.save(QA / f"contact-{first//6+1}.png")
(QA/"pdf-check.json").write_text(json.dumps({"pages":18,"outline":18,"out_of_bounds":issues},indent=2),encoding="utf-8")
print("PDF: 18 pages; all titles and footers found; no out-of-bounds text; rendered every page.")

if "--browser" in sys.argv:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",headless=True)
        page = browser.new_page(viewport={"width":1366,"height":1000},device_scale_factor=1)
        errors=[]
        page.on("pageerror", lambda e:errors.append(str(e)))
        page.goto((OUT/"geonyoung-db-study-guide.html").as_uri())
        assert page.locator("main section").count() == 18
        assert page.locator("details.quiz").count() == 19
        assert page.locator("details[open]").count() == 0
        page.locator("#reveal").click()
        assert page.locator("details[open]").count() == 19
        page.locator("#conceal").click()
        assert page.locator("details[open]").count() == 0
        page.locator("#quiz1 details summary").first.click()
        assert page.locator("#quiz1 details[open]").count() == 1
        page.goto((OUT/"geonyoung-db-study-guide.html").as_uri())
        page.screenshot(path=str(QA/"html-desktop.png"))
        page.set_viewport_size({"width":390,"height":844})
        page.screenshot(path=str(QA/"html-mobile.png"))
        overflow=page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, "Mobile document overflow"
        for section in ["recent","logs","quiz1"]:
            page.locator(f"#{section}").scroll_into_view_if_needed()
            page.screenshot(path=str(QA/f"html-mobile-{section}.png"))
        assert not errors, errors
        browser.close()
    print("HTML: 18 sections; 19 answer toggles work; desktop/mobile checked; no JS errors or document overflow.")
