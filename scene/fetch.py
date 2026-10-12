import json, os, io, re, requests
from PIL import Image, ImageDraw

H = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json'}
req = json.load(open('scene/req.json'))
os.makedirs('scene/sheets', exist_ok=True)
os.makedirs('scene/img', exist_ok=True)
log = []


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


for q in req.get('search', []):
    try:
        r = requests.get('https://unsplash.com/napi/search/photos', params={'query': q, 'per_page': 30}, headers=H, timeout=30)
        res = r.json().get('results', [])
    except Exception as e:
        log.append(f'search {q}: {e}')
        continue
    res = [x for x in res if not x.get('premium') and not x.get('plus')]
    meta, thumbs = [], []
    for i, x in enumerate(res):
        meta.append({'i': i, 'id': x['id'], 'w': x['width'], 'h': x['height'], 'alt': x.get('alt_description'), 'by': x['user']['name']})
        try:
            t = Image.open(io.BytesIO(requests.get(x['urls']['thumb'], timeout=30).content)).convert('RGB')
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
        info = requests.get(f"https://unsplash.com/napi/photos/{g['id']}", headers=H, timeout=30).json()
        if info.get('premium') or info.get('plus'):
            log.append(f"skip premium {g['id']}")
            continue
        url = info['urls']['raw'] + f"&w={g.get('w', 2000)}&q=82&fm=jpg"
        im = Image.open(io.BytesIO(requests.get(url, timeout=60).content)).convert('RGB')
        im.save(f"scene/img/{g['name']}.jpg", quality=86)
        json.dump({'id': g['id'], 'by': info['user']['name'], 'link': info['links']['html']}, open(f"scene/img/{g['name']}.json", 'w'))
        if g.get('cut'):
            from rembg import remove, new_session
            if sess is None:
                sess = new_session('isnet-general-use')
            out = remove(im, session=sess)
            bb = out.getbbox()
            if bb:
                out = out.crop(bb)
            out.save(f"scene/img/{g['name']}.png")
        log.append(f"got {g['name']}")
    except Exception as e:
        log.append(f"get {g}: {e}")

open('scene/log.txt', 'w').write('\n'.join(log))
print('\n'.join(log))
