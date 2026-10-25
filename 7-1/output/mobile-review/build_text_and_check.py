"""Export the private HTML study note as UTF-8 plain text; inspect mobile layout."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "db-review-mobile.html"


class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.skip = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.active = True
        if tag == "nav":
            self.skip = True
        if self.active and not self.skip:
            if tag in {"h1", "h2", "h3", "p", "pre", "dt", "dd", "summary", "footer"}:
                self.parts.append("\n\n")
            elif tag == "li":
                self.parts.append("\n- ")
            elif tag == "br":
                self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "nav":
            self.skip = False
        if tag == "main":
            self.active = False

    def handle_data(self, data):
        if self.active and not self.skip:
            self.parts.append(data)


html = SOURCE.read_text(encoding="utf-8")
assert "\ufffd" not in html
assert not re.search(r"postgres(?:ql)?(?:\+psycopg)?://", html)
assert not re.search(r"<(?:script|link)\b", html)
reader = Reader()
reader.feed(html)
plain = re.sub(r"\n[ \t]+", "\n", "".join(reader.parts))
plain = re.sub(r"\n{3,}", "\n\n", plain).strip() + "\n"
(ROOT / "db-review-mobile.txt").write_text(plain, encoding="utf-8-sig")
result = {"text_export": "ok", "private_file": str(SOURCE), "viewports": []}

if "--browser" in sys.argv:
    sys.path.insert(0, str(ROOT.parent / "study-build" / "vendor"))
    from playwright.sync_api import sync_playwright

    qa = ROOT / "qa"
    qa.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True,
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(SOURCE.as_uri())
        assert page.locator("main section").count() == 17
        assert page.locator("details").count() == 14
        anchors_ok = page.evaluate("""() => Array.from(document.querySelectorAll('a[href^="#"]')).every(a => document.querySelector(a.getAttribute('href')))""")
        assert anchors_ok
        for width in (320, 390, 760):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
            for target in ("save", "ownership", "recent", "exam"):
                page.locator("#" + target).screenshot(path=str(qa / f"{width}-{target}.png"))
            result["viewports"].append({"width": width, "overflow": False})
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("details summary").first.click()
        assert page.locator("details[open]").count() == 1
        page.emulate_media(color_scheme="dark")
        page.locator("#ownership").screenshot(path=str(qa / "390-dark.png"))
        assert not errors, errors
        browser.close()
    result.update({"questions": 14, "anchors": "ok", "toggle": "ok", "errors": errors})
    (qa / "checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
