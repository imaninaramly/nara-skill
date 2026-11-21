#!/usr/bin/env python3
"""Read public Pinterest pin pages the way a link preview does, and save their pictures for study.

  pin_fetch.py OUTDIR URL [URL ...]          pin links (pinterest.com/pin/..., pin.it/...) one per argument
  pin_fetch.py OUTDIR --file links.txt        one link per line
  pin_fetch.py OUTDIR --api-boards            list the boards of your OWN account, secret ones too (official API, needs PINTEREST_TOKEN)
  pin_fetch.py OUTDIR --api-board BOARD_ID    pins of one of your own boards (official API)
  pin_fetch.py OUTDIR --api-search QUERY      search pins through the official API (what Pinterest allows your token to search)

The official API is the only way in for private boards and search: the user makes a token for their own account (developers.pinterest.com,
scopes boards:read, boards:read_secret, pins:read, pins:read_secret) and puts it in the PINTEREST_TOKEN environment variable. It never logs in with
a password or cookies, never calls Pinterest's internal endpoints, and never works around a block; if the API says no, the error is shown as it is.

Writes OUTDIR/pin_XX.jpg, OUTDIR/pins.json (title, description, source link, palette) and OUTDIR/sheet.jpg (contact sheet).
"""
import json, os, re, subprocess, sys, html, urllib.parse
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
ALLOWED = re.compile(r'^https://((www|[a-z]{2})\.)?pinterest\.[a-z.]+/pin/|^https://pin\.it/', re.I)

def curl(url, out=None, extra=()):
    cmd = ['curl', '-s', '-L', '-m', '40', '-A', UA, *extra]
    if out: cmd += ['-o', out, '-w', '%{http_code}']
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    return r.stdout if not out else r.stdout.strip()

def meta(page, name):
    m = re.search(r'<meta[^>]*(?:property|name)="%s"[^>]*content="([^"]*)"' % re.escape(name), page) or \
        re.search(r'<meta[^>]*content="([^"]*)"[^>]*(?:property|name)="%s"' % re.escape(name), page)
    return html.unescape(m.group(1)) if m else ''

def palette(path, n=5):
    try:
        from PIL import Image
        im = Image.open(path).convert('RGB'); im.thumbnail((120, 120))
        q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[:n * 3]; counts = sorted(q.getcolors(), reverse=True)
        return ['#%02x%02x%02x' % tuple(pal[i * 3:i * 3 + 3]) for _, i in counts]
    except Exception:
        return []

def from_page(url, i, out):
    if not ALLOWED.search(url): return {'source': url, 'error': 'not a pin link'}
    page = curl(url)
    img = meta(page, 'og:image')
    if not img: return {'source': url, 'error': 'no picture on the page (private pin, removed, or Pinterest asked for a login)'}
    big = re.sub(r'/(?:\d+x|originals)/', '/736x/', img)           # 736 px wide is plenty for studying a layout
    dest = os.path.join(out, 'pin_%02d.jpg' % i)
    code = curl(big, dest)
    if code != '200': code = curl(img, dest)
    return {'source': url, 'title': meta(page, 'og:title'), 'description': meta(page, 'og:description')[:300],
            'image': dest if code == '200' else '', 'palette': palette(dest) if code == '200' else []}

def api(path, params=''):
    tok = os.environ.get('PINTEREST_TOKEN', '')
    if not tok: sys.exit('Set PINTEREST_TOKEN to an official API v5 token of your own account (never paste it in chat).')
    raw = curl('https://api.pinterest.com/v5' + path + params, extra=['-H', 'Authorization: Bearer ' + tok, '-H', 'Accept: application/json'])
    try: data = json.loads(raw or '{}')
    except ValueError: sys.exit('Unexpected answer from the Pinterest API: ' + raw[:200])
    if isinstance(data, dict) and data.get('code') and not data.get('items'):
        sys.exit('Pinterest API said no (%s): %s' % (data.get('code'), data.get('message')))
    return data

def pins_from_items(data, out):
    res = []
    for i, p in enumerate(data.get('items', []), 1):
        imgs = (p.get('media') or {}).get('images') or {}
        u = (imgs.get('600x') or imgs.get('400x300') or next(iter(imgs.values()), {})).get('url', '')
        dest = os.path.join(out, 'pin_%02d.jpg' % i)
        ok = bool(u) and curl(u, dest) == '200'
        res.append({'source': 'https://www.pinterest.com/pin/%s/' % p.get('id'), 'title': p.get('title') or '', 'description': (p.get('description') or '')[:300],
                    'image': dest if ok else '', 'palette': palette(dest) if ok else []})
    return res

def from_api(mode, arg, out):
    if mode == '--api-boards':
        for b in api('/boards', '?page_size=100').get('items', []):
            print(b.get('id'), b.get('privacy', ''), b.get('name', ''), '(%s pins)' % (b.get('pin_count', '?')))
        sys.exit(0)
    if mode == '--api-board': return pins_from_items(api('/boards/%s/pins' % arg, '?page_size=25'), out)
    return pins_from_items(api('/search/pins', '?query=' + urllib.parse.quote(arg) + '&limit=25'), out)

def sheet(items, out):
    from PIL import Image, ImageDraw
    ok = [x for x in items if x.get('image')]
    if not ok: return
    cell = 360; cols = min(4, len(ok)); rows = (len(ok) + cols - 1) // cols
    s = Image.new('RGB', (cols * cell, rows * (cell + 18)), (240, 240, 240)); d = ImageDraw.Draw(s)
    for k, x in enumerate(ok):
        im = Image.open(x['image']).convert('RGB'); im.thumbnail((cell - 8, cell - 8))
        ox, oy = (k % cols) * cell, (k // cols) * (cell + 18); s.paste(im, (ox + 4, oy + 4)); d.text((ox + 4, oy + cell), str(k + 1), fill=(0, 0, 0))
    s.save(os.path.join(out, 'sheet.jpg'), quality=88)

def main():
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    out, rest = a[0], a[1:]; os.makedirs(out, exist_ok=True)
    if rest[0] in ('--api-boards', '--api-board', '--api-search'): items = from_api(rest[0], rest[1] if len(rest) > 1 else '', out)
    else:
        urls = [l.strip() for l in open(rest[1])] if rest[0] == '--file' else rest
        items = [from_page(u, i, out) for i, u in enumerate([u for u in urls if u], 1)]
    json.dump(items, open(os.path.join(out, 'pins.json'), 'w'), indent=1, ensure_ascii=False)
    sheet(items, out)
    for i, x in enumerate(items, 1): print(i, x.get('error') or (x.get('title') or '(no title)')[:70], x.get('palette', [])[:3])
    print('saved to', out)

main()
