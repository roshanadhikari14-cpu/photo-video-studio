"""Edit the Kerala trip photos: graded photos, Instagram posts with type, collages, web thumbnails."""
import os, sys, json
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont

SRC = sys.argv[1]
OUT = os.path.join(SRC, "edited")
FONTS = r"C:\Users\MY PC\.claude\skills\effects\fonts"
for d in ("photos", "posts", "collages", "thumbs"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

def WA(stamp):
    return f"WhatsApp Image 2026-11-11 at {stamp}.jpeg"

def F(name, size):
    f = ImageFont.truetype(os.path.join(FONTS, name), int(size))
    if name == "Montserrat.ttf":  # variable font: default is hairline, pick a bold weight
        try:
            f.set_variation_by_axes([650])
        except Exception:
            pass
    return f

ANTON, SERIF, SERIF_I, PLAY, PLAY_I, MONT, MARKER, MONO = (
    "Anton-Regular.ttf", "PlayfairDisplay.ttf", "InstrumentSerif-Italic.ttf", "PlayfairDisplay.ttf",
    "PlayfairDisplay-Italic.ttf", "Montserrat.ttf", "PermanentMarker-Regular.ttf", "SpaceMono-Bold.ttf")

# ---------- loading and grading ----------
_cache = {}
def load(name):
    if name not in _cache:
        _cache[name] = ImageOps.exif_transpose(Image.open(os.path.join(SRC, name))).convert("RGB")
    return _cache[name]

def grade(im, sat=1.12, con=1.08, bri=1.0, warm=0.02, level=0.6, sharpen=True, fade=0.0):
    a = np.asarray(im).astype(np.float32)
    if level:
        # gentle auto-levels per channel, blended so colours don't shift too much
        lo = np.percentile(a, 0.4, axis=(0, 1)); hi = np.percentile(a, 99.6, axis=(0, 1))
        st = (a - lo) / np.maximum(hi - lo, 1) * 255
        a = a * (1 - level) + st * level
    if warm:
        a[..., 0] *= 1 + warm; a[..., 2] *= 1 - warm
    if fade:  # lifted blacks, film look
        a = a * (1 - fade) + fade * 40 + a * 0  # keep simple
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    im = ImageEnhance.Contrast(im).enhance(con)
    im = ImageEnhance.Color(im).enhance(sat)
    if bri != 1.0:
        im = ImageEnhance.Brightness(im).enhance(bri)
    if sharpen:
        r = max(1.0, im.width / 1500)
        im = im.filter(ImageFilter.UnsharpMask(radius=r, percent=55, threshold=3))
    return im

def vignette(im, strength=0.28):
    w, h = im.size
    y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]
    m = 1 - strength * np.clip((x ** 2 + y ** 2) / 2, 0, 1) ** 1.3
    a = np.asarray(im).astype(np.float32) * m[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def fit(im, W, H, fx=0.5, fy=0.5):
    """Crop to W:H around the focus point (fx, fy as 0-1 of the image) and resize."""
    w, h = im.size; r = W / H
    if w / h > r:
        cw, ch = int(h * r), h
    else:
        cw, ch = w, int(w / r)
    x = int(np.clip(fx * w - cw / 2, 0, w - cw)); y = int(np.clip(fy * h - ch / 2, 0, h - ch))
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)

def save(im, sub, name, q=95):
    p = os.path.join(OUT, sub, name)
    im.save(p, quality=q, subsampling=0, optimize=True)
    t = im.copy(); t.thumbnail((720, 900))
    t.save(os.path.join(OUT, "thumbs", f"{sub}__{os.path.splitext(name)[0]}.jpg"), quality=82)
    return p

# ---------- typography helpers ----------
def text_w(font, s, track=0):
    return sum(font.getlength(c) for c in s) + track * (len(s) - 1)

def draw_text(img, xy, s, font, fill=(255, 255, 255), track=0, anchor="mm", shadow=0.35, blur=None):
    """Letter-spaced text with a soft shadow. anchor: 'mm' centre, 'lm' left, 'rm' right (x), y is the middle."""
    W, H = img.size
    tw = text_w(font, s, track)
    x, y = xy
    if anchor[0] == "m": x -= tw / 2
    elif anchor[0] == "r": x -= tw
    if shadow:
        sh = Image.new("L", img.size, 0); d = ImageDraw.Draw(sh); cx = x
        for c in s:
            d.text((cx, y), c, font=font, fill=255, anchor="lm"); cx += font.getlength(c) + track
        sh = sh.filter(ImageFilter.GaussianBlur(blur or max(4, font.size * 0.12)))
        img.paste(Image.new("RGB", img.size, (0, 0, 0)), (0, int(font.size * 0.03)), sh.point(lambda v: int(v * shadow)))
    d = ImageDraw.Draw(img); cx = x
    for c in s:
        d.text((cx, y), c, font=font, fill=fill, anchor="lm"); cx += font.getlength(c) + track
    return tw

def gradient(img, top=0.0, bottom=0.45, strength=0.65, color=(0, 0, 0)):
    """Darken the top/bottom so text reads. top/bottom are fractions of height covered."""
    W, H = img.size
    if STORY:  # stretch the shade to cover text moved into the story safe zone
        top = 0.13 + 0.72 * top if top else 0
        bottom = 0.15 + 0.72 * bottom if bottom else 0
    a = np.zeros(H, np.float32)
    if bottom:
        n = int(H * bottom); a[H - n:] = np.linspace(0, 1, n) ** 1.6
    if top:
        n = int(H * top); a[:n] = np.maximum(a[:n], np.linspace(1, 0, n) ** 1.6)
    m = Image.fromarray((np.repeat(a[:, None], W, 1) * 255 * strength).astype(np.uint8))
    img.paste(Image.new("RGB", img.size, color), (0, 0), m)

def fit_font(name, s, max_w, start, track_k=0.0):
    size = start
    while size > 20:
        f = F(name, size)
        if text_w(f, s, size * track_k) <= max_w: return f
        size *= 0.95
    return F(name, size)

W, H = 2160, 2700  # Instagram 4:5 at 2x for crisp uploads
SH = 3840          # story height: 9:16 at 2x
STORY = False
os.makedirs(os.path.join(OUT, "stories"), exist_ok=True)

def Y(f):
    """Vertical position as a fraction of the post. In a story, squeeze into the safe zone
    (Instagram covers the top ~13% with your name and the bottom ~15% with the reply bar)."""
    return H * (0.13 + 0.72 * f) if STORY else H * f

manifest = {"photos": [], "posts": [], "collages": [], "stories": []}
stories = manifest["stories"]

# ---------- 1. graded photos (full resolution) ----------
PHOTOS = [
    ("IMG_0490.JPG", "Kovalam bay from the lighthouse", dict(sat=1.15, con=1.1, warm=0.02)),
    ("IMG_0481.JPG", "Palm over the Arabian Sea", dict(sat=1.18, con=1.08)),
    ("IMG_0496.JPG", "Rocky coastline", dict(sat=1.15, con=1.1)),
    ("IMG_0484.JPG", "Town in the palms", dict(sat=1.15, con=1.06)),
    ("IMG_0449.JPG", "Poovar backwaters", dict(sat=1.2, con=1.1, warm=0.03)),
    ("IMG_0447.JPG", "Backwater reflections", dict(sat=1.2, con=1.1, warm=0.03)),
    ("IMG_0427.JPG", "Palm-lined river", dict(sat=1.2, con=1.08)),
    ("IMG_0429.JPG", "Mangrove green", dict(sat=1.15, con=1.08)),
    ("IMG_0469.JPG", "Boat to the estuary", dict(sat=1.15, con=1.08)),
    ("IMG_0459.JPG", "Rock in the estuary", dict(sat=1.12, con=1.1)),
    ("IMG_0476.JPG", "Aazhimala Shiva", dict(sat=1.05, con=1.12, warm=0.0)),
    ("IMG_0500.JPG", "Sree Padmanabhaswamy Temple", dict(sat=1.15, con=1.08, warm=0.03)),
    ("IMG_0418.JPG", "Kovalam nights", dict(sat=1.0, con=1.05, warm=0.0, level=0.2)),
    ("IMG_0419.JPG", "Candlelit dinner", dict(sat=0.95, con=1.05, warm=0.0, level=0.2)),
    ("IMG_0416.JPG", "Balcony beach view", dict(sat=1.15, con=1.08)),
    ("IMG_0415.JPG", "Kovalam beach", dict(sat=1.12, con=1.06)),
    (WA("8.20.58 PM"), "Lighthouse at dusk", dict(sat=1.05, con=1.05, level=0.3)),
    (WA("8.21.01 PM"), "Sea gazing", dict(sat=1.08, con=1.06, level=0.3)),
    (WA("8.21.03 PM (2)"), "Palm and peace", dict(sat=1.05, con=1.05, level=0.3)),
    (WA("8.21.00 PM (2)"), "Hotel steps", dict(sat=1.05, con=1.05, level=0.3)),
    (WA("8.20.58 PM (1)"), "Boat ride together", dict(sat=1.08, con=1.05, level=0.3)),
    (WA("8.22.31 PM"), "Selfie on the rocks", dict(sat=1.05, con=1.05, level=0.3)),
    (WA("8.20.58 PM (2)"), "Beach walk", dict(sat=1.08, con=1.05, level=0.3)),
    (WA("8.21.05 PM"), "Coffee with a view", dict(sat=1.08, con=1.06, level=0.3)),
]
graded = {}
for i, (f, title, g) in enumerate(PHOTOS, 1):
    im = grade(load(f), **g); graded[f] = im
    name = f"{i:02d}_{title.lower().replace(' ', '-')}.jpg"
    save(im, "photos", name)
    manifest["photos"].append({"file": f"photos/{name}", "title": title, "src": f, "size": f"{im.width}x{im.height}"})
    print("photo", name, flush=True)

def G(f, **g):
    return graded[f] if f in graded and not g else grade(load(f), **(g or {}))

# ---------- 2. single posts with typography ----------
posts = []

def post(fname, title, caption, fx=0.5, fy=0.5, build=None, **g):
    global H, STORY
    src = G(fname, **g)
    n = len(posts) + 1; nice = title.replace("-", " ").title()
    img = fit(src, W, H, fx, fy)
    build(img)
    name = f"post_{n:02d}_{title}.jpg"
    save(img, "posts", name)
    posts.append({"file": f"posts/{name}", "title": nice, "caption": caption})
    # story version: same design, 9:16, text kept inside the safe zone
    STORY, H = True, SH
    try:
        st = fit(src, W, H, fx, fy)
        build(st)
        sname = f"story_{n:02d}_{title}.jpg"
        save(st, "stories", sname, q=93)
        stories.append({"file": f"stories/{sname}", "title": nice, "size": f"{W}x{SH}"})
    finally:
        STORY, H = False, 2700
    print("post+story", name, flush=True)

def p_kovalam(img):
    gradient(img, top=0.32, bottom=0.25, strength=0.55)
    f = fit_font(ANTON, "KOVALAM", W * 0.86, 520, 0.04)
    draw_text(img, (W / 2, Y(0.14)), "KOVALAM", f, track=f.size * 0.04, shadow=0.45)
    draw_text(img, (W / 2, Y(0.245)), "Kerala  ·  God's Own Country", F(PLAY_I, 92), fill=(255, 246, 225))
    draw_text(img, (W / 2, Y(0.93)), "8.3800° N   76.9790° E", F(MONO, 54), fill=(255, 255, 255), track=8)

def p_backwaters(img):
    gradient(img, top=0.3, bottom=0.0, strength=0.45)
    draw_text(img, (W / 2, Y(0.1)), "slow days on", F(PLAY_I, 120), fill=(255, 250, 235))
    f = fit_font(SERIF, "the backwaters", W * 0.9, 250)
    draw_text(img, (W / 2, Y(0.19)), "the backwaters", f, fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.27)), "POOVAR  ·  KERALA", F(MONT, 58), track=22, fill=(255, 255, 255))

def p_shiva(img):
    gradient(img, top=0.0, bottom=0.36, strength=0.85 if STORY else 0.7)
    f = fit_font(ANTON, "AAZHIMALA", W * 0.82, 400, 0.06)
    draw_text(img, (W / 2, Y(0.82)), "AAZHIMALA", f, track=f.size * 0.06, shadow=0.5)
    draw_text(img, (W / 2, Y(0.9)), "Shiva Temple  ·  by the sea", F(PLAY_I, 96), fill=(240, 236, 228))

def p_temple(img):
    gradient(img, top=0.3, bottom=0.0, strength=0.6, color=(40, 20, 0))
    draw_text(img, (W / 2, Y(0.085)), "SREE PADMANABHASWAMY", fit_font(MONT, "SREE PADMANABHASWAMY", W * 0.86, 110, 0.12),
              track=13, fill=(255, 220, 140))
    f = fit_font(PLAY_I, "Temple", W * 0.8, 330)
    draw_text(img, (W / 2, Y(0.18)), "Temple", f, fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.272)), "Thiruvananthapuram", F(MONT, 64), track=14, fill=(255, 240, 210))

def p_neon(img):
    gradient(img, top=0.0, bottom=0.25, strength=0.7)
    draw_text(img, (W / 2, Y(0.91)), "kovalam after dark", F(PLAY_I, 150), fill=(255, 210, 235))

def p_dusk(img):
    gradient(img, top=0.26, bottom=0.0, strength=0.5, color=(10, 20, 50))
    draw_text(img, (W / 2, Y(0.09)), "blue hour", F(PLAY_I, 230), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.17)), "AT THE LIGHTHOUSE", F(MONT, 66), track=24, fill=(230, 240, 255))

def p_sea(img):
    if STORY:  # tall crop puts her head where the text was: use the pale sky at the top instead
        ink = (24, 62, 74)
        draw_text(img, (W / 2, H * 0.17), "salt in the air,", F(PLAY_I, 170), fill=ink, shadow=0)
        draw_text(img, (W / 2, H * 0.215), "sea in my hair", F(PLAY_I, 170), fill=(150, 40, 40), shadow=0)
        return
    gradient(img, top=0.0, bottom=0.3, strength=0.55)
    draw_text(img, (W * 0.07, Y(0.86)), "salt in the air,", F(PLAY_I, 150), anchor="lm", fill=(255, 255, 255))
    draw_text(img, (W * 0.07, Y(0.925)), "sea in my hair", F(PLAY_I, 150), anchor="lm", fill=(255, 235, 225))

def p_palm(img):
    gradient(img, top=0.0, bottom=0.3, strength=0.5)
    f = fit_font(MARKER, "LIFE'S A BEACH", W * 0.84, 260)
    draw_text(img, (W / 2, Y(0.88)), "LIFE'S A BEACH", f, fill=(255, 255, 255), shadow=0.5)

def p_coffee(img):
    gradient(img, top=0.28, bottom=0.0, strength=0.62)
    draw_text(img, (W / 2, Y(0.1)), "coffee with a view", F(PLAY_I, 170), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.18)), "KOVALAM BEACH", F(MONT, 60), track=22, fill=(255, 245, 225))

def p_cover(img):
    gradient(img, top=0.0, bottom=0.55, strength=0.75)
    draw_text(img, (W / 2, Y(0.62)), "a trip to", F(PLAY_I, 150), fill=(255, 240, 220))
    f = fit_font(ANTON, "KERALA", W * 0.86, 640, 0.05)
    draw_text(img, (W / 2, Y(0.75)), "KERALA", f, track=f.size * 0.05, shadow=0.5)
    draw_text(img, (W / 2, Y(0.875)), "BEACHES  ·  BACKWATERS  ·  TEMPLES", F(MONT, 56), track=12)
    draw_text(img, (W / 2, Y(0.93)), "MAY 2026", F(MONO, 50), track=14, fill=(255, 220, 160))

post("IMG_0449.JPG", "kerala-cover", "Kerala, you have my heart 🌴 Beaches, backwaters and temples, all in one trip.\n\n#Kerala #GodsOwnCountry #KeralaTourism #TravelDiaries #IncredibleIndia",
     fy=0.55, build=p_cover)
post("IMG_0490.JPG", "kovalam", "The view that made the climb worth it 🌊 #Kovalam #Kerala #GodsOwnCountry #BeachLife",
     fy=0.6, build=p_kovalam)
post("IMG_0447.JPG", "backwaters", "Where time slows down 🛶 #Poovar #KeralaBackwaters #Kerala #SlowTravel",
     fy=0.55, build=p_backwaters)
post("IMG_0476.JPG", "aazhimala", "Peace, by the sea 🙏 #Aazhimala #ShivaTemple #Kerala #Spiritual",
     fy=0.45, build=p_shiva)
post("IMG_0500.JPG", "padmanabhaswamy", "Golden gopuram, blue skies ✨ #Padmanabhaswamy #Thiruvananthapuram #Kerala #TempleTrail",
     fy=0.5, build=p_temple)
post(WA("8.20.58 PM"), "blue-hour", "Blue dress, blue hour 💙 #Kovalam #Lighthouse #BlueHour #Kerala",
     fy=0.5, build=p_dusk)
post(WA("8.21.01 PM"), "salt-in-the-air", "Salt in the air, sea in my hair 🌊 #SeaView #Kovalam #KeralaDiaries",
     fy=0.5, build=p_sea)
post("IMG_0481.JPG", "lifes-a-beach", "Life's a beach 🌴 #Kovalam #PalmTrees #Kerala #BeachVibes",
     fy=0.5, build=p_palm)
post(WA("8.21.05 PM"), "coffee-with-a-view", "Coffee tastes better with this view ☕🌊 #CoffeeWithAView #Kovalam #CafeHopping",
     fy=0.55, build=p_coffee)
post("IMG_0418.JPG", "after-dark", "Kovalam after dark ✨ #Kovalam #NightLife #Kerala",
     fy=0.55, build=p_neon, sat=1.0, con=1.05, level=0.2, warm=0.0)
manifest["posts"] = posts

# ---------- 3. collages ----------
collages = []

def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    return m

def place(canvas, fname, box, fx=0.5, fy=0.5, r=0, border=0, g=None):
    x0, y0, x1, y1 = [int(v) for v in box]
    tile = fit(G(fname, **(g or {})), x1 - x0, y1 - y0, fx, fy)
    if border:
        canvas.paste((255, 255, 255), (x0 - border, y0 - border, x1 + border, y1 + border))
    canvas.paste(tile, (x0, y0), rounded(tile, r) if r else None)

def collage(slug, title, caption, bg, build):
    c = Image.new("RGB", (W, H), bg)
    build(c)
    name = f"collage_{len(collages) + 1:02d}_{slug}.jpg"
    save(c, "collages", name)
    # story version: the collage floating on a blurred copy of itself
    bgi = fit(c, W, SH).filter(ImageFilter.GaussianBlur(60))
    bgi = ImageEnhance.Brightness(bgi).enhance(0.75)
    cw = int(W * 0.86); chh = int(cw * H / W)
    small = c.resize((cw, chh), Image.LANCZOS)
    x, y = (W - cw) // 2, (SH - chh) // 2
    sh = Image.new("L", bgi.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((x, y + 30, x + cw, y + chh + 30), 40, fill=150)
    bgi.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(40)))
    bgi.paste(small, (x, y), rounded(small, 40))
    sname = name.replace("collage_", "story_collage_")
    save(bgi, "stories", sname, q=93)
    stories.append({"file": f"stories/{sname}", "title": title + " (collage)", "size": f"{W}x{SH}"})
    collages.append({"file": f"collages/{name}", "title": title, "caption": caption})
    print("collage", name, flush=True)

def c_backwaters(c):
    m, gap = 90, 36
    draw_text(c, (W / 2, 190), "backwaters", F(PLAY_I, 230), fill=(32, 58, 44), shadow=0)
    draw_text(c, (W / 2, 360), "POOVAR  ·  KERALA", F(MONT, 52), fill=(80, 110, 90), track=20, shadow=0)
    top = 450; bw = W - 2 * m
    place(c, "IMG_0449.JPG", (m, top, W - m, top + 1150), fy=0.55, r=36)
    hw = (bw - gap) / 2; y2 = top + 1150 + gap
    place(c, "IMG_0427.JPG", (m, y2, m + hw, H - m), fy=0.5, r=36)
    place(c, "IMG_0429.JPG", (m + hw + gap, y2, W - m, H - m), fy=0.5, r=36)

def c_beach(c):
    gap = 24
    cw, ch = (W - gap) / 2, (H - gap) / 2
    cells = [(WA("8.20.58 PM (2)"), 0.5, 0.5), (WA("8.21.05 PM"), 0.5, 0.55), (WA("8.22.27 PM"), 0.5, 0.5), ("IMG_0415.JPG", 0.5, 0.6)]
    for i, (f, fx, fy) in enumerate(cells):
        x = (i % 2) * (cw + gap); y = (i // 2) * (ch + gap)
        place(c, f, (x, y, x + cw, y + ch), fx, fy)
    # centre badge
    r = 330; cx, cy = W / 2, H / 2
    ImageDraw.Draw(c).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 244, 232))
    draw_text(c, (cx, cy - 70), "Kovalam", F(PLAY_I, 150), fill=(20, 70, 90), shadow=0)
    draw_text(c, (cx, cy + 80), "DIARIES", F(MONT, 70), fill=(200, 110, 60), track=26, shadow=0)

def c_temple(c):
    m, gap = 80, 30
    draw_text(c, (W / 2, 175), "THIRUVANANTHAPURAM", fit_font(MONT, "THIRUVANANTHAPURAM", W * 0.8, 96, 0.1), fill=(255, 215, 140), track=12, shadow=0)
    draw_text(c, (W / 2, 315), "temple trail", F(PLAY_I, 150), fill=(255, 246, 230), shadow=0)
    top = 420; bw = W - 2 * m; hw = (bw - gap) / 2
    place(c, "IMG_0500.JPG", (m, top, m + hw, H - m), fy=0.45, r=24)
    rh = (H - m - top - gap) / 2
    place(c, WA("8.22.36 PM (1)"), (m + hw + gap, top, W - m, top + rh), fy=0.45, r=24)
    place(c, "IMG_0476.JPG", (m + hw + gap, top + rh + gap, W - m, H - m), fy=0.4, r=24)

def c_her(c):
    m, gap = 70, 26
    draw_text(c, (W / 2, 160), "main character energy", F(PLAY_I, 140), fill=(120, 30, 40), shadow=0)
    top = 270; cw = (W - 2 * m - 2 * gap) / 3; ch = (H - m - top - gap) / 2
    cells = [WA("8.21.03 PM (2)"), WA("8.21.00 PM (1)"), WA("8.21.00 PM"),
             WA("8.21.00 PM (2)"), WA("8.21.01 PM"), WA("8.20.59 PM (1)")]
    for i, f in enumerate(cells):
        x = m + (i % 3) * (cw + gap); y = top + (i // 3) * (ch + gap)
        place(c, f, (x, y, x + cw, y + ch), 0.5, 0.45, r=22)

def c_couple(c):
    # polaroid scatter
    import random; random.seed(7)
    cells = [(WA("8.20.58 PM (1)"), 0.5, 0.5), (WA("8.22.31 PM"), 0.4, 0.5), (WA("8.20.59 PM"), 0.5, 0.5),
             (WA("8.21.04 PM"), 0.5, 0.55), (WA("8.22.37 PM (1)"), 0.45, 0.5), (WA("8.22.36 PM (1)"), 0.5, 0.45)]
    labels = ["boat ride", "on the rocks", "beach walks", "spooky stop", "movie night", "temple day"]
    pos = [(560, 760), (1600, 730), (560, 1530), (1600, 1500), (560, 2300), (1600, 2270)]
    pw, ph = 860, 560
    for (f, fx, fy), lab, (cx, cy) in zip(cells, labels, pos):
        card = Image.new("RGB", (pw + 60, ph + 190), (255, 255, 255))
        card.paste(fit(G(f), pw, ph, fx, fy), (30, 30))
        draw_text(card, (card.width / 2, ph + 105), lab, F(MARKER, 70), fill=(40, 40, 40), shadow=0)
        card = card.rotate(random.uniform(-5, 5), resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0)) if False else card
        ang = random.uniform(-5, 5)
        rc = card.convert("RGBA").rotate(ang, resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", rc.size, (0, 0, 0, 0)); sh.putalpha(rc.getchannel("A").point(lambda v: int(v * 0.35)))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        c.paste(sh, (int(cx - rc.width / 2 + 12), int(cy - rc.height / 2 + 20)), sh)
        c.paste(rc, (int(cx - rc.width / 2), int(cy - rc.height / 2)), rc)
    draw_text(c, (W / 2, 170), "us, in Kerala", F(PLAY_I, 170), fill=(60, 40, 30), shadow=0)

def c_food(c):
    m, gap = 80, 30
    draw_text(c, (W / 2, 170), "sips & bites", F(PLAY_I, 190), fill=(255, 238, 215), shadow=0)
    top = 300; cw = (W - 2 * m - gap) / 2; ch = (H - m - top - 2 * gap) / 3
    cells = [WA("8.22.33 PM (2)"), WA("8.22.27 PM"), "IMG_0419.JPG", WA("8.22.31 PM (2)"), WA("8.22.30 PM"), WA("8.21.05 PM")]
    for i, f in enumerate(cells):
        x = m + (i % 2) * (cw + gap); y = top + (i // 2) * (ch + gap)
        g = dict(sat=0.95, con=1.05, level=0.2, warm=0.0) if f == "IMG_0419.JPG" else None
        place(c, f, (x, y, x + cw, y + ch), 0.5, 0.5, r=28, g=g)

def c_cliffs(c):
    gap = 20
    place(c, "IMG_0490.JPG", (0, 0, W, H * 0.5 - gap / 2), fy=0.6)
    hw = (W - gap) / 2
    place(c, "IMG_0481.JPG", (0, H * 0.5 + gap / 2, hw, H), fy=0.5)
    place(c, "IMG_0496.JPG", (hw + gap, H * 0.5 + gap / 2, W, H), fy=0.6)
    band = Image.new("RGB", (W, 260), (250, 246, 238)); c.paste(band, (0, int(H * 0.5 - 130)))
    draw_text(c, (W / 2, H * 0.5 - 30), "WHERE THE LAND MEETS THE SEA", fit_font(MONT, "WHERE THE LAND MEETS THE SEA", W * 0.82, 80, 0.15),
              fill=(25, 70, 95), track=14, shadow=0)
    draw_text(c, (W / 2, H * 0.5 + 60), "Kovalam lighthouse", F(PLAY_I, 72), fill=(160, 100, 60), shadow=0)

collage("backwaters", "Backwaters", "Three shades of green 🌿 #Poovar #KeralaBackwaters #Kerala", (236, 242, 232), c_backwaters)
collage("kovalam-diaries", "Kovalam Diaries", "Kovalam diaries 🌊☕🌴 #Kovalam #BeachDays #Kerala", (250, 244, 232), c_beach)
collage("temple-trail", "Temple Trail", "Temple trail in Thiruvananthapuram 🙏 #Padmanabhaswamy #Aazhimala #Kerala", (70, 30, 20), c_temple)
collage("main-character", "Main Character", "Main character energy ❤️ #OOTD #TravelStyle #Kerala", (252, 236, 232), c_her)
collage("us-in-kerala", "Us in Kerala", "Us, in Kerala 💛 #CoupleGoals #TravelTogether #Kerala", (239, 228, 212), c_couple)
collage("sips-and-bites", "Sips & Bites", "Sips & bites ☕🌸 #CafeHopping #Kovalam #FoodDiaries", (60, 40, 32), c_food)
collage("land-meets-sea", "Land Meets Sea", "Where the land meets the sea 🌊 #Kovalam #Lighthouse #Kerala", (250, 246, 238), c_cliffs)
manifest["collages"] = collages

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("DONE")
