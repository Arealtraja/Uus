import json, os, io, re, requests
from PIL import Image, ImageDraw

H = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json'}
req = json.load(open('scene/req.json'))
os.makedirs('scene/sheets', exist_ok=True)
os.makedirs('scene/img', exist_ok=True)
log = []


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


for sh in req.get('sheets', []):
    thumbs = []
    for u in sh['urls']:
        try:
            t = Image.open(io.BytesIO(requests.get('https://images.unsplash.com/' + u + '?w=420&q=70', headers=H, timeout=30).content)).convert('RGB')
            t.thumbnail((400, 400))
        except Exception as e:
            t = Image.new('RGB', (400, 260), 'gray')
            log.append(f'thumb {u}: {e}')
        thumbs.append(t)
    cols = 5
    rows = (len(thumbs) + cols - 1) // cols or 1
    sheet = Image.new('RGB', (cols * 410, rows * 410), 'white')
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(thumbs):
        x, y = (i % cols) * 410, (i // cols) * 410
        sheet.paste(t, (x + 5, y + 5))
        d.rectangle([x + 5, y + 5, x + 44, y + 32], fill='black')
        d.text((x + 12, y + 12), str(i), fill='yellow')
    sheet.save(f"scene/sheets/{sh['name']}.jpg", quality=82)
    json.dump(sh['urls'], open(f"scene/sheets/{sh['name']}.json", 'w'), indent=1)
    log.append(f"sheet {sh['name']}: {len(thumbs)}")

for q in req.get('search', []):
    r = None
    try:
        r = requests.get('https://api.openverse.org/v1/images/', params={'q': q, 'license': 'cc0,pdm,by', 'page_size': 30, 'mature': 'false'}, headers=H, timeout=40)
        res = r.json().get('results', [])
    except Exception as e:
        log.append(f'search {q}: {e} {r.status_code if r is not None else ""} {r.text[:200] if r is not None else ""}')
        continue
    meta, thumbs = [], []
    for i, x in enumerate(res):
        meta.append({'i': i, 'url': x.get('url'), 'w': x.get('width'), 'h': x.get('height'), 'title': x.get('title'), 'by': x.get('creator'), 'lic': x.get('license'), 'src': x.get('source'), 'page': x.get('foreign_landing_url')})
        try:
            t = Image.open(io.BytesIO(requests.get(x.get('thumbnail') or x['url'], headers=H, timeout=30).content)).convert('RGB')
            t.thumbnail((240, 240))
            thumbs.append(t)
        except Exception:
            thumbs.append(Image.new('RGB', (240, 160), 'gray'))
    cols = 6
    rows = (len(thumbs) + cols - 1) // cols or 1
    sheet = Image.new('RGB', (cols * 250, rows * 250), 'white')
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(thumbs):
        x, y = (i % cols) * 250, (i // cols) * 250
        sheet.paste(t, (x + 5, y + 5))
        d.rectangle([x + 5, y + 5, x + 40, y + 30], fill='black')
        d.text((x + 10, y + 10), str(i), fill='yellow')
    s = slug(q)
    sheet.save(f'scene/sheets/{s}.jpg', quality=80)
    json.dump(meta, open(f'scene/sheets/{s}.json', 'w'), indent=1)
    log.append(f'search {q}: {len(res)}')

sess = None
for g in req.get('get', []):
    try:
        im = Image.open(io.BytesIO(requests.get(g['url'] if g['url'].startswith('http') else 'https://images.unsplash.com/' + g['url'] + '?w=2400&q=85&fm=jpg', headers=H, timeout=90).content)).convert('RGB')
        if max(im.size) > g.get('w', 2400):
            im.thumbnail((g.get('w', 2400), g.get('w', 2400)))
        im.save(f"scene/img/{g['name']}.jpg", quality=86)
        json.dump(g, open(f"scene/img/{g['name']}.json", 'w'))
        if g.get('cut'):
            from rembg import remove, new_session
            if sess is None:
                sess = new_session('isnet-general-use')
            out = remove(im, session=sess)
            bb = out.getbbox()
            if bb:
                out = out.crop(bb)
            out.save(f"scene/img/{g['name']}.png")
        log.append(f"got {g['name']} {im.size}")
    except Exception as e:
        log.append(f"get {g}: {e}")


os.makedirs('scene/fonts', exist_ok=True)
for f in req.get('fonts', []):
    try:
        b = requests.get(f['url'], headers=H, timeout=60).content
        p = f"scene/fonts/{f['name']}.otf"
        open(p, 'wb').write(b)
        from fontTools.ttLib import TTFont
        t = TTFont(p)
        t.flavor = 'woff2'
        t.save(f"scene/fonts/{f['name']}.woff2")
        log.append(f"font {f['name']} {len(b)}")
    except Exception as e:
        log.append(f"font {f}: {e}")

open('scene/log.txt', 'w').write('\n'.join(log))
print('\n'.join(log))
