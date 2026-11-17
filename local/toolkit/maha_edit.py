"""Mahabalipuram photos: graded photos, posts + stories, collages, manifest."""
import os, sys, json, random
import numpy as np


from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont

SRC = sys.argv[1]
OUT = os.path.join(SRC, "edited")
FONTS = r"C:\Users\MY PC\.claude\skills\effects\fonts"
for d in ("photos", "posts", "stories", "collages", "thumbs"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

ANTON, SERIF, PLAY_I, MONT, MARKER, MONO = ("Anton-Regular.ttf", "PlayfairDisplay.ttf", "PlayfairDisplay-Italic.ttf",
                                           "Montserrat.ttf", "PermanentMarker-Regular.ttf", "SpaceMono-Bold.ttf")
def F(name, size):
    f = ImageFont.truetype(os.path.join(FONTS, name), int(size))
    if name == MONT:
        f.set_variation_by_axes([650])
    return f

# ---------- grading ----------
_cache = {}
def load(name):
    if name not in _cache:
        _cache[name] = ImageOps.exif_transpose(Image.open(os.path.join(SRC, name))).convert("RGB")
    return _cache[name]

def soft_light(a, b):
    """a, b in 0..1. Photoshop-style soft light blend."""
    return np.where(b < 0.5, 2 * a * b + a * a * (1 - 2 * b), 2 * a * (1 - b) + np.sqrt(a) * (2 * b - 1))

def grade(im, sat=1.12, con=1.08, warm=0.02, level=0.6, clip=0.4, dehaze=0.0, clarity=0.0,
          wash=None, wash_amt=0.0, bri=1.0, sky=None):
    a = np.asarray(im).astype(np.float32) / 255
    if level:
        lo = np.percentile(a, clip, axis=(0, 1)); hi = np.percentile(a, 100 - clip, axis=(0, 1))
        a = a * (1 - level) + np.clip((a - lo) / np.maximum(hi - lo, 1e-3), 0, 1) * level
    if dehaze:  # lift contrast mostly in the bright, washed-out areas (sky haze)
        lum = a.mean(2, keepdims=True)
        a = np.clip(a - dehaze * 0.25 * lum ** 2, 0, 1)
        a = np.clip((a - a.min()) / (a.max() - a.min()), 0, 1)
    if warm:
        a[..., 0] *= 1 + warm; a[..., 2] *= 1 - warm
    if wash is not None and wash_amt:  # colour gradient (top colour -> bottom colour), soft-light blended
        h = a.shape[0]; t = np.linspace(0, 1, h)[:, None, None]
        top, bot = np.array(wash[0]) / 255, np.array(wash[1]) / 255
        g = top * (1 - t) + bot * t
        a = a * (1 - wash_amt) + soft_light(np.clip(a, 0, 1), np.broadcast_to(g, a.shape)) * wash_amt
    if sky:  # multiply a sunrise colour into the bright top of the frame (washed-out skies turn peach)
        h = a.shape[0]; t = np.clip(np.linspace(0, 1, h) / 0.65, 0, 1)[:, None, None]
        tint = np.array(sky[0]) / 255
        lum = a.mean(2, keepdims=True)
        k = sky[1] * (1 - t) ** 1.3 * np.clip((lum - 0.35) / 0.5, 0, 1)
        a = a * (1 - k) + a * tint * k
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    im = ImageEnhance.Contrast(im).enhance(con)
    im = ImageEnhance.Color(im).enhance(sat)
    if bri != 1:
        im = ImageEnhance.Brightness(im).enhance(bri)
    if clarity:  # local contrast
        im = im.filter(ImageFilter.UnsharpMask(radius=max(im.size) / 60, percent=int(clarity * 100), threshold=0))
    return im.filter(ImageFilter.UnsharpMask(radius=max(1.0, im.width / 1800), percent=50, threshold=3))

def fit(im, W, H, fx=0.5, fy=0.5):
    w, h = im.size; r = W / H
    cw, ch = (int(h * r), h) if w / h > r else (w, int(w / r))
    x = int(np.clip(fx * w - cw / 2, 0, w - cw)); y = int(np.clip(fy * h - ch / 2, 0, h - ch))
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)

def save(im, sub, name, q=95):
    im.save(os.path.join(OUT, sub, name), quality=q, subsampling=0, optimize=True)
    t = im.copy(); t.thumbnail((720, 900))
    t.save(os.path.join(OUT, "thumbs", f"{sub}__{os.path.splitext(name)[0]}.jpg"), quality=82)

# ---------- type ----------
def text_w(font, s, track=0):
    return sum(font.getlength(c) for c in s) + track * (len(s) - 1)

def draw_text(img, xy, s, font, fill=(255, 255, 255), track=0, anchor="mm", shadow=0.35):
    tw = text_w(font, s, track); x, y = xy
    if anchor[0] == "m": x -= tw / 2
    elif anchor[0] == "r": x -= tw
    if shadow:
        sh = Image.new("L", img.size, 0); d = ImageDraw.Draw(sh); cx = x
        for c in s:
            d.text((cx, y), c, font=font, fill=255, anchor="lm"); cx += font.getlength(c) + track
        sh = sh.filter(ImageFilter.GaussianBlur(max(4, font.size * 0.12)))
        img.paste((0, 0, 0), (0, int(font.size * 0.03)), sh.point(lambda v: int(v * shadow)))
    d = ImageDraw.Draw(img); cx = x
    for c in s:
        d.text((cx, y), c, font=font, fill=fill, anchor="lm"); cx += font.getlength(c) + track

def fit_font(name, s, max_w, start, track_k=0.0):
    size = start
    while size > 20:
        f = F(name, size)
        if text_w(f, s, size * track_k) <= max_w: return f
        size *= 0.95
    return F(name, size)

W, H, SH = 2160, 2700, 3840
STORY = False
def Y(f):
    return H * (0.13 + 0.72 * f) if STORY else H * f

def gradient(img, top=0.0, bottom=0.45, strength=0.65, color=(0, 0, 0)):
    w, h = img.size
    if STORY:
        top = 0.13 + 0.72 * top if top else 0
        bottom = 0.15 + 0.72 * bottom if bottom else 0
    a = np.zeros(h, np.float32)
    if bottom:
        n = int(h * bottom); a[h - n:] = np.linspace(0, 1, n) ** 1.6
    if top:
        n = int(h * top); a[:n] = np.maximum(a[:n], np.linspace(1, 0, n) ** 1.6)
    m = Image.fromarray((np.repeat(a[:, None], w, 1) * 255 * strength).astype(np.uint8))
    img.paste(Image.new("RGB", img.size, color), (0, 0), m)

def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    return m

# ---------- 1. graded photos ----------
DAY = dict(sky=((255, 214, 182), 0.28), sat=1.2, con=1.1, level=0.7, dehaze=0.6, clarity=0.3, warm=0.03,
           wash=((150, 180, 225), (255, 196, 145)), wash_amt=0.25)
SUNSET = dict(sky=((255, 188, 135), 0.35), sat=1.25, con=1.12, level=0.8, dehaze=0.5, clarity=0.3, warm=0.04,
              wash=((255, 170, 110), (60, 48, 70)), wash_amt=0.35)
GOLDEN = dict(sat=1.22, con=1.1, level=0.7, dehaze=0.45, clarity=0.35, warm=0.03, wash=((255, 178, 120), (80, 62, 72)), wash_amt=0.3)
MOODY = dict(sat=1.08, con=1.15, level=0.8, dehaze=0.6, clarity=0.3, wash=((120, 140, 172), (70, 62, 66)), wash_amt=0.3)
PHOTOS = [
    ("IMG_7952.JPG", "Shore Temple", DAY),
    ("IMG_7954.JPG", "The Nandi wall", DAY),
    ("IMG_7951.JPG", "Temple by the sea", DAY),
    ("IMG_7956.JPG", "Bay of Bengal", DAY),
    ("IMG_7959.JPG", "Pancha Rathas", DAY),
    ("IMG_7961.JPG", "Rock-cut ratha", DAY),
    ("IMG_7963.JPG", "The stone elephant", DAY),
    ("IMG_7970.JPG", "From the lighthouse hill", DAY),
    ("IMG_7971.JPG", "Sunset over the town", SUNSET),
    ("IMG_7964.JPG", "Golden hour", dict(SUNSET, bri=1.08)),
    ("IMG_7979.JPG", "Lighthouse at sunset", SUNSET),
    ("IMG_7983.JPG", "Mamallapuram lighthouse", DAY),
    ("IMG_7984.JPG", "Rock-cut cave", DAY),
    ("IMG_7985.JPG", "The ancient gateway", DAY),
    ("IMG_7987.JPG", "Krishna's Butter Ball", GOLDEN),
    ("IMG_7991.JPG", "Butter Ball glow", GOLDEN),
    ("IMG_7996.JPG", "Balanced", GOLDEN),
    ("IMG_8002.JPG", "Butter Ball at dusk", GOLDEN),
    ("IMG_8006.JPG", "Arjuna's Penance", GOLDEN),
    ("IMG_7995.JPG", "Selfie with the Butter Ball", dict(GOLDEN, dehaze=0.25, clarity=0.15)),
    ("IMG_8009.JPG", "Evening at the beach", MOODY),
    ("IMG_8008.JPG", "Waves", MOODY),
]
graded, manifest = {}, {"meta": {
    "title": "Mahabalipuram", "kicker": "STORIES IN STONE · TAMIL NADU",
    "footer": "Your original photos are untouched. Edits are saved in Mahabalipuram\\edited.",
    "accent": "#b05c32", "accent_dark": "#f0a070", "bg": "#f2eadf", "bg_dark": "#17150f"},
    "photos": [], "posts": [], "stories": [], "collages": []}
for i, (f, title, g) in enumerate(PHOTOS, 1):
    im = grade(load(f), **g); graded[f] = im
    slug = title.lower().replace("'", "").replace(" ", "-")
    name = f"{i:02d}_{slug}.jpg"
    save(im, "photos", name)
    manifest["photos"].append({"file": f"photos/{name}", "title": title, "size": f"{im.width}x{im.height}"})
    print("photo", name, flush=True)
G = graded.__getitem__

# ---------- 2. posts + stories ----------
posts, stories = manifest["posts"], manifest["stories"]
def post(fname, slug, caption, build, fx=0.5, fy=0.5, sfx=None, sfy=None):
    global H, STORY
    n = len(posts) + 1; nice = slug.replace("-", " ").title()
    img = fit(G(fname), W, H, fx, fy); build(img)
    name = f"post_{n:02d}_{slug}.jpg"; save(img, "posts", name)
    posts.append({"file": f"posts/{name}", "title": nice, "caption": caption})
    STORY, H = True, SH
    try:
        st = fit(G(fname), W, H, sfx if sfx is not None else fx, sfy if sfy is not None else fy); build(st)
        sname = f"story_{n:02d}_{slug}.jpg"; save(st, "stories", sname, q=93)
        stories.append({"file": f"stories/{sname}", "title": nice, "size": f"{W}x{SH}"})
    finally:
        STORY, H = False, 2700
    print("post+story", name, flush=True)

SAND = (255, 232, 205); PEACH = (255, 208, 170)
def p_cover(img):
    gradient(img, top=0.0, bottom=0.42, strength=0.8, color=(25, 14, 12))
    draw_text(img, (W / 2, Y(0.715)), "stories in stone", F(PLAY_I, 130), fill=PEACH)
    f = fit_font(ANTON, "MAHABALIPURAM", W * 0.9, 420, 0.03)
    draw_text(img, (W / 2, Y(0.805)), "MAHABALIPURAM", f, track=f.size * 0.03, shadow=0.5)
    draw_text(img, (W / 2, Y(0.9)), "SHORE TEMPLE  ·  BUTTER BALL  ·  LIGHTHOUSE", fit_font(MONT, "SHORE TEMPLE  ·  BUTTER BALL  ·  LIGHTHOUSE", W * 0.84, 54, 0.25), track=13)

def p_shore(img):
    gradient(img, top=0.0, bottom=0.42, strength=0.88, color=(30, 18, 10))
    draw_text(img, (W / 2, Y(0.8)), "Shore Temple", F(PLAY_I, 220), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.885)), "8TH CENTURY  ·  BY THE BAY OF BENGAL", fit_font(MONT, "8TH CENTURY  ·  BY THE BAY OF BENGAL", W * 0.8, 58, 0.3), track=16, fill=SAND)

def p_golden(img):
    gradient(img, top=0.0, bottom=0.34, strength=0.75, color=(20, 14, 18))
    draw_text(img, (W / 2, Y(0.8)), "golden hour", F(PLAY_I, 230), fill=PEACH)
    draw_text(img, (W / 2, Y(0.885)), "FROM THE LIGHTHOUSE HILL", F(MONT, 60), track=22)

def p_rathas(img):
    gradient(img, top=0.0, bottom=0.4, strength=0.85, color=(25, 18, 12))
    f = fit_font(ANTON, "PANCHA RATHAS", W * 0.8, 300, 0.05)
    draw_text(img, (W / 2, Y(0.8)), "PANCHA RATHAS", f, track=f.size * 0.05, shadow=0.5)
    draw_text(img, (W / 2, Y(0.895)), "carved from single rocks", F(PLAY_I, 130), fill=SAND)

def p_lighthouse(img):
    gradient(img, top=0.34, bottom=0.0, strength=0.72, color=(25, 22, 35))
    draw_text(img, (W / 2, Y(0.09)), "lighthouse views", F(PLAY_I, 200), fill=(255, 255, 255), shadow=0.5)
    draw_text(img, (W / 2, Y(0.17)), "MAMALLAPURAM", F(MONT, 64), track=26, fill=(255, 255, 255), shadow=0.6)

def p_butter(img):
    gradient(img, top=0.0, bottom=0.33, strength=0.75, color=(25, 15, 12))
    draw_text(img, (W / 2, Y(0.8)), "Krishna's Butter Ball", fit_font(PLAY_I, "Krishna's Butter Ball", W * 0.86, 190), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.885)), "DEFYING GRAVITY", F(MONT, 62), track=28, fill=PEACH)

def p_penance(img):
    gradient(img, top=0.0, bottom=0.34, strength=0.75, color=(22, 18, 28))
    draw_text(img, (W / 2, Y(0.8)), "Arjuna's Penance", fit_font(PLAY_I, "Arjuna's Penance", W * 0.84, 210), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.885)), "A WHOLE STORY CARVED IN ROCK", fit_font(MONT, "A WHOLE STORY CARVED IN ROCK", W * 0.8, 58, 0.3), track=16, fill=PEACH)

def p_beach(img):
    gradient(img, top=0.0, bottom=0.36, strength=0.7, color=(15, 18, 24))
    draw_text(img, (W / 2, Y(0.8)), "salt, sand & stories", fit_font(PLAY_I, "salt, sand & stories", W * 0.86, 190), fill=(255, 255, 255))
    draw_text(img, (W / 2, Y(0.885)), "MAHABALIPURAM BEACH", F(MONT, 60), track=24, fill=(210, 222, 235))

post("IMG_7996.JPG", "mahabalipuram", "Stories in stone 🪨🌅 Mahabalipuram, you were magic.\n\n#Mahabalipuram #Mamallapuram #TamilNadu #Heritage #TravelDiaries",
     p_cover, fy=0.42)
post("IMG_7952.JPG", "shore-temple", "Standing by the sea for over 1200 years 🌊🛕 #ShoreTemple #Mahabalipuram #UNESCO #TamilNadu",
     p_shore, fy=0.4)
post("IMG_7971.JPG", "golden-hour", "Golden hour from the lighthouse hill 🌅 #Sunset #Mahabalipuram #GoldenHour",
     p_golden, fy=0.5)
post("IMG_7963.JPG", "pancha-rathas", "Carved from single rocks 🐘 #PanchaRathas #Mahabalipuram #IndianArchitecture",
     p_rathas, fy=0.6)
post("IMG_7979.JPG", "lighthouse-views", "Lighthouse views 🗼 #Mahabalipuram #Lighthouse #TamilNadu",
     p_lighthouse, fy=0.62)
post("IMG_7991.JPG", "butter-ball", "Krishna's Butter Ball, still not rolling 😄🪨 #KrishnasButterBall #Mahabalipuram #GoldenSky",
     p_butter, fy=0.45)
post("IMG_8006.JPG", "arjunas-penance", "A whole story carved in rock ✨ #ArjunasPenance #Mahabalipuram #Heritage",
     p_penance, fy=0.45)
post("IMG_8009.JPG", "salt-and-sand", "Salt, sand & stories 🌊 #MahabalipuramBeach #BayOfBengal #Monsoon",
     p_beach, fy=0.55)

# ---------- 3. collages ----------
collages = manifest["collages"]
def place(c, f, box, fx=0.5, fy=0.5, r=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    t = fit(G(f), x1 - x0, y1 - y0, fx, fy)
    c.paste(t, (x0, y0), rounded(t, r) if r else None)

def collage(slug, title, caption, bg, build):
    c = Image.new("RGB", (W, H), bg); build(c)
    name = f"collage_{len(collages) + 1:02d}_{slug}.jpg"; save(c, "collages", name)
    collages.append({"file": f"collages/{name}", "title": title, "caption": caption})
    s = fit(c, W, SH).filter(ImageFilter.GaussianBlur(60)); s = ImageEnhance.Brightness(s).enhance(0.75)
    cw = int(W * 0.86); chh = int(cw * H / W); sm = c.resize((cw, chh), Image.LANCZOS)
    x, y = (W - cw) // 2, (SH - chh) // 2
    sh = Image.new("L", s.size, 0); ImageDraw.Draw(sh).rounded_rectangle((x, y + 30, x + cw, y + chh + 30), 40, fill=150)
    s.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(40))); s.paste(sm, (x, y), rounded(sm, 40))
    sname = name.replace("collage_", "story_collage_"); save(s, "stories", sname, q=93)
    stories.append({"file": f"stories/{sname}", "title": title + " (collage)", "size": f"{W}x{SH}"})
    print("collage", name, flush=True)

BG = (242, 234, 223); TERRA = (176, 92, 50); INK = (58, 40, 30)
def c_temple(c):
    m, gap = 80, 30
    draw_text(c, (W / 2, 175), "temple town", F(PLAY_I, 170), fill=INK, shadow=0)
    draw_text(c, (W / 2, 315), "MAHABALIPURAM", F(MONT, 56), fill=TERRA, track=26, shadow=0)
    top = 420; bw = W - 2 * m
    place(c, "IMG_7952.JPG", (m, top, W - m, top + 1150), fy=0.42, r=32)
    hw = (bw - gap) / 2; y2 = top + 1150 + gap
    place(c, "IMG_7963.JPG", (m, y2, m + hw, H - m), fy=0.6, r=32)
    place(c, "IMG_7961.JPG", (m + hw + gap, y2, W - m, H - m), fx=0.6, fy=0.62, r=32)

def c_butter(c):
    gap = 22; cw, ch = (W - gap) / 2, (H - gap) / 2
    cells = [("IMG_7987.JPG", 0.4, 0.5), ("IMG_7996.JPG", 0.5, 0.45), ("IMG_8002.JPG", 0.55, 0.45), ("IMG_7991.JPG", 0.5, 0.5)]
    for i, (f, fx, fy) in enumerate(cells):
        x = (i % 2) * (cw + gap); y = (i // 2) * (ch + gap); place(c, f, (x, y, x + cw, y + ch), fx, fy)
    r = 340; cx, cy = W / 2, H / 2
    ImageDraw.Draw(c).ellipse((cx - r, cy - r, cx + r, cy + r), fill=BG)
    draw_text(c, (cx, cy - 70), "butter ball", F(PLAY_I, 140), fill=TERRA, shadow=0)
    draw_text(c, (cx, cy + 75), "DIARIES", F(MONT, 66), fill=INK, track=26, shadow=0)

def c_reel(c):
    holes = 110; d = ImageDraw.Draw(c)
    for yy in range(40, H, 150):
        d.rounded_rectangle((35, yy, 95, yy + 80), 14, fill=BG)
        d.rounded_rectangle((W - 95, yy, W - 35, yy + 80), 14, fill=BG)
    frames = [("IMG_7970.JPG", 0.62), ("IMG_7971.JPG", 0.55), ("IMG_7964.JPG", 0.5), ("IMG_8006.JPG", 0.3)]
    top, bot, gap = 130, H - 260, 40; fh = (bot - top - gap * 3) / 4
    for i, (f, fy) in enumerate(frames):
        y = top + i * (fh + gap); place(c, f, (holes + 20, y, W - holes - 20, y + fh), fy=fy)
    draw_text(c, (W / 2, H - 140), "sunset, frame by frame", F(PLAY_I, 110), fill=PEACH, shadow=0)

def c_polaroid(c):
    random.seed(7)
    cells = [("IMG_7954.JPG", 0.5, 0.55, "shore temple"), ("IMG_7983.JPG", 0.5, 0.4, "the lighthouse"),
             ("IMG_7995.JPG", 0.45, 0.45, "me & the rock"), ("IMG_8009.JPG", 0.5, 0.6, "beach evening")]
    pos = [(590, 900), (1570, 860), (590, 1980), (1570, 1940)]
    pw, ph = 880, 820
    for (f, fx, fy, lab), (cx, cy) in zip(cells, pos):
        card = Image.new("RGB", (pw + 60, ph + 200), (255, 255, 255))
        card.paste(fit(G(f), pw, ph, fx, fy), (30, 30))
        draw_text(card, (card.width / 2, ph + 110), lab, F(MARKER, 74), fill=(45, 40, 40), shadow=0)
        rc = card.convert("RGBA").rotate(random.uniform(-5, 5), resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", rc.size, (0, 0, 0, 0)); sh.putalpha(rc.getchannel("A").point(lambda v: int(v * 0.35)))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        c.paste(sh, (int(cx - rc.width / 2 + 12), int(cy - rc.height / 2 + 20)), sh)
        c.paste(rc, (int(cx - rc.width / 2), int(cy - rc.height / 2)), rc)
    draw_text(c, (W / 2, 190), "memories by the sea", F(PLAY_I, 140), fill=INK, shadow=0)

def c_magazine(c):
    place(c, "IMG_7961.JPG", (0, 0, W, H), 0.55, 0.55)
    gradient(c, top=0.3, bottom=0.32, strength=0.78, color=(28, 16, 10))
    f = fit_font(ANTON, "MAHABALIPURAM", W * 0.92, 400, 0.02)
    draw_text(c, (W / 2, 230), "MAHABALIPURAM", f, track=f.size * 0.02, fill=(255, 238, 220))
    draw_text(c, (W / 2, 420), "THE HERITAGE ISSUE", F(MONT, 52), track=24, fill=PEACH)
    draw_text(c, (110, H - 360), "Stories in stone", F(PLAY_I, 110), anchor="lm", fill=(255, 255, 255))
    draw_text(c, (110, H - 240), "SHORE TEMPLE  ·  RATHAS  ·  BUTTER BALL", F(MONT, 46), anchor="lm", track=10, fill=PEACH)

collage("temple-town", "Temple Town", "Temple town 🛕 #Mahabalipuram #ShoreTemple #PanchaRathas", BG, c_temple)
collage("butter-ball-diaries", "Butter Ball Diaries", "Butter ball diaries 🪨🌅 #KrishnasButterBall #Mahabalipuram", BG, c_butter)
collage("sunset-reel", "Sunset Reel", "Sunset, frame by frame 🎞️🌅 #Sunset #Mahabalipuram", (22, 20, 22), c_reel)
collage("memories", "Memories", "Memories by the sea 📸 #Mahabalipuram #TravelMemories", (236, 226, 212), c_polaroid)
collage("heritage-issue", "The Heritage Issue", "The heritage issue 📖🛕 #Mahabalipuram #Heritage #TamilNadu", (30, 20, 16), c_magazine)

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("DONE")
