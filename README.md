# AI GRC Watch

A weekly briefing on AI regulation, governance, risk and compliance, published every Monday.

**Read it:** https://smashytech.github.io/ai-grc-watch/

## How it works

```
Monday 08:49 (Stockholm)
        │
        ▼
Scheduled Claude task ──► researches the week ──► fills the HTML template
        │                                                │
        │                          ┌─────────────────────┴───────────────┐
        ▼                          ▼                                     ▼
   reads issues/index.json   emails the issue (Gmail)     python3 scripts/add_issue.py
   (issue no. + last 2)                                    → issues/YYYY-MM-DD-issue-N.html
                                                           → issues/index.json
                                                                   │
                                                          git push → GitHub Pages
```

## Files

| Path | What it is |
|---|---|
| `index.html` | Archive homepage. Reads `issues/index.json` in the browser and lists every issue. |
| `issues/index.json` | One entry per issue: number, date, window, item count, headline, summary, file. Newest first. |
| `issues/*.html` | The issues themselves, exactly as emailed, plus an "All issues" bar on top. |
| `scripts/add_issue.py` | The gatekeeper. Validates an issue, cleans Gmail link wrappers, writes the file and updates the index. Refuses duplicates and escaped HTML. |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are. |

## Adding an issue by hand

```bash
python3 scripts/add_issue.py path/to/issue.html        # an issue HTML file
python3 scripts/add_issue.py --gmail message.json      # a Gmail get_message result
python3 scripts/add_issue.py --check                   # check the whole archive
```
