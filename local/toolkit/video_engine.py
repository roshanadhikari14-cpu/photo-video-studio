import os, sys, math, subprocess, wave, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.environ["VE_BASE"]
OUT = os.path.join(BASE, "shorts"); os.makedirs(OUT, exist_ok=True)
TMP = os.path.dirname(os.path.abspath(__file__))
FONTS = r"C:\Users\MY PC\.claude\skills\effects\fonts"
W, H, FPS = 1080, 1920, 30
ONLY = []

def F(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), int(size))
    if wght:
        try: f.set_variation_by_axes([wght])
        except Exception: pass
    return f
ANTON = lambda s: F("Anton-Regular.ttf", s)
SERIF_I = lambda s: F("PlayfairDisplay-Italic.ttf", s)
MONT = lambda s: F("Montserrat.ttf", s, 650)
MONO = lambda s: F("SpaceMono-Bold.ttf", s)

# ---------- images ----------
_cache = {}
def img(n):
    if n not in _cache:
        p = glob.glob(os.path.join(BASE, "photos", f"{n:02d}_*.jpg"))[0]
        im = Image.open(p).convert("RGB")
        h = 2400 if im.width > im.height else 2600
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        _cache[n] = im
    return _cache[n]

def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, t)))
def lerp(a, b, t): return a + (b - a) * t

def camera(shot, lt):
    """x/y = view centre (0..1), s = fraction of image height shown."""
    im = img(shot["p"])
    e = ease(lt / shot["d"]) if shot.get("ease", True) else max(0, min(1, lt / shot["d"]))
    s = lerp(shot.get("s0", 1), shot.get("s1", 1), e)
    ch = im.height * s; cw = ch * W / H
    if cw > im.width: cw = im.width; ch = cw * H / W
    cx = lerp(shot.get("x0", .5), shot.get("x1", .5), e) * im.width
    cy = lerp(shot.get("y0", .5), shot.get("y1", .5), e) * im.height
    cx = min(max(cx, cw / 2), im.width - cw / 2); cy = min(max(cy, ch / 2), im.height - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)

# ---------- overlays ----------
def shade():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
    yy = np.linspace(-1, 1, H)[:, None]
    top = np.clip((0.22 - y) / 0.22, 0, 1) ** 1.5 * 0.45
    bot = np.clip((y - 0.55) / 0.45, 0, 1) ** 1.6 * 0.70
    vig = np.clip((x ** 2 * 0.6 + yy ** 2 * 0.35) - 0.25, 0, 1) * 0.5
    a = np.clip(top + bot + vig, 0, 0.85)
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
SHADE = shade()

def text_layer(s, font, fill=(255, 255, 255), track=0, reveal=None, shadow=0.45):
    widths = [font.getlength(c) for c in s]
    tw = sum(widths) + track * (len(s) - 1)
    asc, desc = font.getmetrics()
    pad = 40
    L = Image.new("RGBA", (int(tw) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", L.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(L), ImageDraw.Draw(sh)
    x = pad; n = len(s) if reveal is None else reveal
    for i, c in enumerate(s[:n]):
        d.text((x, pad), c, font=font, fill=fill)
        ds.text((x, pad + 4), c, font=font, fill=(0, 0, 0, int(255 * shadow)))
        x += widths[i] + track
    if shadow:
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        sh.alpha_composite(L); L = sh
    return L

def fit(s, ff, maxw, start, track_k=0.0):
    size = start
    while True:
        f = ff(size); w = sum(f.getlength(c) for c in s) + track_k * size * (len(s) - 1)
        if w <= maxw or size < 20: return f, track_k * size
        size -= 4

class T:
    """animated text. y = fraction of frame height (centre). anim: rise|pop|type|wide"""
    def __init__(self, t0, t1, s, ff, size, y, anim="rise", fill=(255, 255, 255), track_k=0.0, maxw=920, x=0.5):
        f, tr = fit(s, ff, maxw, size, track_k)
        self.t0, self.t1, self.y, self.x, self.anim = t0, t1, y, x, anim
        if anim == "type":
            self.layers = [text_layer(s, f, fill, tr, reveal=i) for i in range(len(s) + 1)]
        else:
            self.layer = text_layer(s, f, fill, tr)
    def draw(self, fr, t):
        if t < self.t0 or t > self.t1: return
        a_in = min(1, (t - self.t0) / 0.45); a_out = min(1, (self.t1 - t) / 0.35)
        alpha = ease(a_in) * ease(a_out); dy = 0; scale = 1.0
        if self.anim == "type":
            n = min(len(self.layers) - 1, int((t - self.t0) / 0.06)); L = self.layers[n]; alpha = ease(a_out)
        else:
            L = self.layer
            if self.anim == "rise": dy = (1 - ease(a_in)) * 50
            if self.anim == "pop":
                scale = 1 + 0.35 * (1 - ease(min(1, (t - self.t0) / 0.35)))
                alpha = ease(min(1, (t - self.t0) / 0.2)) * ease(a_out)
        if scale != 1: L = L.resize((max(1, int(L.width * scale)), max(1, int(L.height * scale))), Image.BILINEAR)
        if alpha < 1:
            L = L.copy(); L.putalpha(L.getchannel("A").point(lambda v: int(v * alpha)))
        fr.alpha_composite(L, (int(W * self.x - L.width / 2), int(H * self.y - L.height / 2 + dy)))

# ---------- music (generated here, royalty-free) ----------
SR = 44100
NOTE = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}
def hz(n, o): return 440 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)
def music(path, dur, chords, bpm, kick=False):
    t = np.arange(int(SR * dur)) / SR; out = np.zeros_like(t)
    seg = dur / len(chords)
    for i, ch in enumerate(chords):
        a, b = i * seg - 0.6, (i + 1) * seg + 0.6
        env = np.clip(np.minimum((t - a) / 0.9, (b - t) / 0.9), 0, 1)
        for (n, o) in ch:
            f = hz(n, o)
            for det in (-0.12, 0.12):
                out += env * 0.06 * (np.sin(2 * np.pi * (f + det) * t) + 0.35 * np.sin(4 * np.pi * (f + det) * t) + 0.12 * np.sin(6 * np.pi * f * t))
        beat = 60 / bpm / 2; k = 0; tt = i * seg
        while tt < (i + 1) * seg - 1e-6:
            n, o = ch[[0, 1, 2, 1][k % 4] % len(ch)]; f = hz(n, o + 2)
            m = t >= tt; x = t[m] - tt
            out[m] += 0.07 * np.sin(2 * np.pi * f * x) * np.exp(-x * 3.2) * (1 - np.exp(-x * 400))
            tt += beat; k += 1
    if kick:
        beat = 60 / bpm; tt = 0
        while tt < dur - 0.5:
            m = t >= tt; x = t[m] - tt
            ph = 2 * np.pi * (50 * x + (70 / 18) * (1 - np.exp(-18 * x)))
            out[m] += 0.35 * np.sin(ph) * np.exp(-x * 9)
            tt += beat
    rev = out.copy()
    for dl, g in ((0.031, .35), (0.047, .3), (0.083, .25), (0.127, .2), (0.211, .15)):
        s = int(dl * SR); rev[s:] += out[:-s] * g
    out = np.tanh(rev * 1.2)
    out *= np.minimum(1, np.minimum(t / 0.8, (dur - t) / 1.5))
    out = out / np.max(np.abs(out)) * 0.6
    st = np.stack([out, np.roll(out, 220)], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

# ---------- render ----------
def render(name, shots, texts, xf, chords, bpm, kick=False, flash=False):
    if ONLY and name not in ONLY: return
    starts, t = [], 0
    for s in shots: starts.append(t); t += s["d"] - xf
    dur = t + xf
    wav = os.path.join(TMP, name + ".wav"); music(wav, dur, chords, bpm, kick)
    out = os.path.join(OUT, name + ".mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    N = int(round(dur * FPS)); checks = {int(N * f) for f in (.08, .3, .55, .85)}
    for k in range(N):
        tt = k / FPS
        act = [i for i, s0 in enumerate(starts) if s0 <= tt < s0 + shots[i]["d"]]
        i = act[-1]; fr = camera(shots[i], tt - starts[i])
        if len(act) > 1:
            p = act[0]; a = (tt - starts[i]) / xf
            fr = Image.blend(camera(shots[p], tt - starts[p]), fr, ease(a))
            if flash: fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 245, 235)), 0.55 * math.sin(math.pi * a))
        fr = fr.convert("RGBA"); fr.alpha_composite(SHADE)
        for tx in texts: tx.draw(fr, tt)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if k in checks:
            fr.convert("RGB").resize((360, 640)).save(os.path.join(TMP, f"chk_{name}_{k:03d}.jpg"), quality=80)
    ff.stdin.close(); ff.wait()
    os.remove(wav)
    print("done", name, round(dur, 1), "s", flush=True)

def S(p, d, **k): k.update(p=p, d=d); return k
SAND = (255, 236, 214); PEACH = (255, 214, 180)

