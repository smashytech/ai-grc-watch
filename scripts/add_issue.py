#!/usr/bin/env python3
"""Add one AI GRC Watch issue to the site.

Usage:
  python3 scripts/add_issue.py ISSUE.html            # an issue file the weekly task wrote
  python3 scripts/add_issue.py --gmail MESSAGE.json  # a Gmail get_message result (for back-filling)
  python3 scripts/add_issue.py --check               # validate the whole archive

What it does:
  1. Checks the HTML is real HTML (not escaped &lt;div&gt;) and reads the issue
     number, date, window, item count and headline out of it.
  2. Removes Gmail's https://www.google.com/url?q=... link wrappers.
  3. Writes issues/YYYY-MM-DD-issue-N.html with a small "All issues" bar on top.
  4. Adds the issue to issues/index.json (newest first).
It refuses (exit code 1) instead of overwriting or duplicating anything.
"""
import html
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "issues"
INDEX = ISSUES / "index.json"
MARKER = "<!-- agw-nav -->"

NAV = (
    MARKER
    + '<div style="background:#1d1d1f;padding:10px 16px;text-align:center;'
    'font-family:Arial,Helvetica,sans-serif;font-size:12px;letter-spacing:1.5px;'
    'text-transform:uppercase;"><a href="../" style="color:#ffffff;'
    'text-decoration:none;font-weight:bold;">&larr; All issues</a></div>'
)

HEAD = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    "<title>AI GRC Watch</title>\n</head>\n"
    '<body style="margin:0;padding:0;background-color:#e8ecf1;">\n'
)


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def text(fragment):
    """Strip tags and decode entities: '<b>A &amp; B</b>' -> 'A & B'."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def unwrap_google(doc):
    """https://www.google.com/url?q=REAL&amp;source=gmail... -> REAL"""
    def repl(m):
        raw = html.unescape(m.group(1))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("q")
        return 'href="%s"' % html.escape(q[0], quote=True) if q else m.group(0)
    return re.sub(r'href="(https://www\.google\.com/url\?[^"]+)"', repl, doc)


def metadata(doc):
    if "&lt;div" in doc or "&lt;table" in doc:
        fail("the HTML is escaped (&lt;div&gt;); write raw tags")
    if "<table" not in doc:
        fail("no <table> found; this does not look like an issue")

    m = re.search(r"Issue No\.\s*(\d+)", doc)
    if not m:
        fail("could not find 'Issue No. N'")
    issue = int(m.group(1))

    m = re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2} \w+ \d{4})", doc)
    if not m:
        fail("could not find the send date (e.g. 'Monday 16 November 2026')")
    date = datetime.strptime(m.group(2), "%d %B %Y").strftime("%Y-%m-%d")

    m = re.search(r"Covering\s+(.+?)\s*(?:&middot;|·)\s*(\d+)\s+developments", doc)
    if not m:
        fail("could not find 'Covering <window> · N developments'")
    window, items = text(m.group(1)), int(m.group(2))

    h3_count = len(re.findall(r"<h3[\s>]", doc))
    if h3_count != items:
        fail("header says %d developments but the page has %d items" % (items, h3_count))

    m = re.search(r"<h2[^>]*>(.*?)</h2>", doc, re.S)
    headline = text(m.group(1)) if m else ""
    headline = re.sub(r"^The week in brief:\s*", "", headline)

    m = re.search(r'<div style="display:none[^"]*">(.*?)</div>', doc, re.S)
    summary = text(m.group(1)) if m else ""

    return {"issue": issue, "date": date, "window": window, "items": items,
            "headline": headline, "summary": summary}


def load_index():
    if not INDEX.exists():
        return []
    return json.loads(INDEX.read_text(encoding="utf-8"))


def add(doc):
    doc = unwrap_google(doc)
    meta = metadata(doc)
    entries = load_index()
    for e in entries:
        if e["issue"] == meta["issue"]:
            fail("Issue No. %d is already in index.json" % meta["issue"])
        if e["date"] == meta["date"]:
            print("NOTE: another issue is already dated %s (same-day supplement?)" % meta["date"])
    if entries and meta["issue"] != max(e["issue"] for e in entries) + 1:
        print("NOTE: issue %d is not the next number after %d"
              % (meta["issue"], max(e["issue"] for e in entries)))

    name = "%s-issue-%d.html" % (meta["date"], meta["issue"])
    path = ISSUES / name
    if path.exists():
        fail("%s already exists" % name)

    if "<html" not in doc.lower():          # Gmail strips <html>/<head>/<body>
        doc = HEAD + doc.strip() + "\n</body>\n</html>\n"
    if MARKER not in doc:
        doc = re.sub(r"(<body[^>]*>)", r"\1\n" + NAV.replace("\\", "\\\\"), doc, count=1)

    ISSUES.mkdir(exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    meta["file"] = "issues/" + name
    entries.append(meta)
    entries.sort(key=lambda e: e["issue"], reverse=True)
    INDEX.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ADDED Issue No. %d (%s, %d items) -> %s" % (meta["issue"], meta["date"], meta["items"], name))


def check():
    entries = load_index()
    problems = []
    numbers = [e["issue"] for e in entries]
    if len(numbers) != len(set(numbers)):
        problems.append("duplicate issue numbers")
    for e in entries:
        f = ROOT / e["file"]
        if not f.exists():
            problems.append("missing file " + e["file"])
            continue
        d = f.read_text(encoding="utf-8")
        if "&lt;div" in d:
            problems.append(e["file"] + " is escaped")
        if "google.com/url?" in d:
            problems.append(e["file"] + " still has Gmail link wrappers")
    listed = {e["file"] for e in entries}
    for f in ISSUES.glob("*.html"):
        if "issues/" + f.name not in listed:
            problems.append(f.name + " is not in index.json")
    if problems:
        print("PROBLEMS:\n- " + "\n- ".join(problems))
        sys.exit(1)
    print("OK: %d issues" % len(entries))


def main(argv):
    if argv == ["--check"]:
        check()
    elif len(argv) == 2 and argv[0] == "--gmail":
        msg = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        add(msg.get("htmlBody") or fail("no htmlBody in " + argv[1]))
    elif len(argv) == 1 and not argv[0].startswith("-"):
        add(Path(argv[0]).read_text(encoding="utf-8"))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
