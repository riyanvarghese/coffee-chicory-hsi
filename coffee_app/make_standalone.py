"""Wrap index.html into a standalone page and copy it with core.js and models.js into site/, ready for any static host
(GitHub Pages, Netlify Drop, Cloudflare Pages). Re-run after every rebuild of index.html."""
import shutil
from pathlib import Path
from urllib.parse import quote

app = Path(__file__).resolve().parent
out = app / "site"; out.mkdir(exist_ok=True)
icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><ellipse cx="16" cy="16" rx="10.5" ry="14" transform="rotate(32 16 16)" fill="#3b2418"/>'
        '<path d="M12 4.6 C 20 11.5, 12.5 20.5, 20.5 27.4" stroke="#f6f1ea" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>')
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Find the blend type and chicory content of ground coffee from a SWIR hyperspectral scan. Runs in your browser.">\n'
        f'<link rel="icon" href="data:image/svg+xml,{quote(icon)}">\n')
(out / "index.html").write_text(head + (app / "index.html").read_text() + "\n</html>\n")
for f in ("core.js", "models.js"): shutil.copy2(app / f, out / f)
print("wrote", out, sorted(p.name for p in out.iterdir()))
