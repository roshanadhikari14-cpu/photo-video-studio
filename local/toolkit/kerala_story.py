"""Kerala backwaters: 15 s Instagram story from Video 1-4. Beat-cut, zoom / whip / light-leak transitions,
speed ramps, cinematic grade, titles, generated music + whooshes."""
import os, sys, math, wave, subprocess
import numpy as np
from PIL import Image
SRC = r"C:\Users\MY PC\Video Editing Claude\kerala"
os.environ["VE_BASE"] = os.path.join(SRC, "edited")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_engine as ve
from video_engine import T, ANTON, SERIF_I, MONT, SAND, PEACH
from cine_grade import Grade

W, H, FPS = 1080, 1920, 30
OUT = os.path.join(SRC, "edited", "videos"); os.makedirs(OUT, exist_ok=True)
TMP = os.path.dirname(os.path.abspath(__file__))
TEST = "test" in sys.argv

g_base = dict(sky_side="top", sky=(1.0, 0.84, 0.68), sky_amt=0.22, contrast=0.42, vib=0.4, black=0.03, white=0.97,
              dehaze=0.35, clarity=0.2, warm=0.05, teal=0.05, gamma=0.95, vignette=0.2)
G_GREEN = Grade(W, H, **g_base)
G_HAZE = Grade(W, H, **dict(g_base, dehaze=0.4, contrast=0.38, sky=(1.0, 0.84, 0.7), sky_amt=0.18, gamma=0.98, clarity=0.12))
G_SUN = Grade(W, H, **dict(g_base, sky=(1.0, 0.7, 0.45), sky_amt=0.42, warm=0.07, dehaze=0.5, contrast=0.48))

class Clip:
    """Decodes at 60 fps; speed(t) picks how many source frames to advance per output frame."""
    def __init__(self, name, ss, grade):
        vf = f"fps=60,scale={W}:{H}:flags=lanczos,hqdn3d=1.5:1.5:3:3"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", os.path.join(SRC, name), "-vf", vf, "-an",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.grade, self.pos, self.read, self.raw, self.cache = grade, 0.0, -1, None, {}
    def frame(self, adv):
        self.pos += adv
        want = int(self.pos)
        while self.read < want:
            b = self.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3: break
            self.raw = b; self.read += 1
        key = self.read
        if key not in self.cache:
            self.cache = {key: Image.frombytes("RGB", (W, H), self.grade(self.raw, W, H))}
        return self.cache[key]

# cuts on the beat: 96 bpm, 4 beats per shot = 2.5 s
BPM = 96; BAR = 4 * 60 / BPM
CUTS = [i * BAR for i in range(7)]  # 0 .. 15
def ramp(lt, d):  # 1x -> 3x -> 1x speed ramp
    return 1 + 2 * math.sin(math.pi * min(max(lt / d, 0), 1)) ** 2
SHOTS = [  # file, start, grade, speed(local t), zoom from -> to
    dict(v="Video 1.MOV", ss=1.0, g=G_GREEN, sp=lambda t: 1.0, z=(1.0, 1.12)),
    dict(v="Video 2.MOV", ss=1.5, g=G_GREEN, sp=lambda t: 1.3, z=(1.12, 1.0)),
    dict(v="Video 1.MOV", ss=24.0, g=G_GREEN, sp=lambda t: 1.4, z=(1.0, 1.1)),
    dict(v="Video 1.MOV", ss=38.5, g=G_GREEN, sp=lambda t: ramp(t, BAR), z=(1.08, 1.0)),
    dict(v="Video 4.MOV", ss=0.5, g=G_HAZE, sp=lambda t: 0.6, z=(1.0, 1.1)),
    dict(v="Video 3.MOV", ss=0.5, g=G_SUN, sp=lambda t: 0.8, z=(1.12, 1.0)),
]
TRANS = ["leak", "zoom", "whip", "zoom", "leak"]
XF = 0.3  # transition length, centred on each cut

def zoom(im, s, cx=0.5, cy=0.5):
    if abs(s - 1) < 1e-3: return im
    cw, ch = W / s, H / s
    x0 = min(max(W * cx - cw / 2, 0), W - cw); y0 = min(max(H * cy - ch / 2, 0), H - ch)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

def zoom_blur(im, s, amt):  # radial blur by stacking slightly larger copies
    if amt < 0.02: return zoom(im, s)
    acc = np.zeros((H, W, 3), np.float32); n = 5
    for k in range(n):
        acc += np.asarray(zoom(im, s * (1 + amt * 0.12 * k / n)), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))

def hblur(im, amt):  # horizontal motion smear
    if amt < 0.05: return im
    f = max(2, int(2 + 40 * amt))
    return im.resize((W // f, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def leak(im, a):  # warm light leak sweeping across, screen blend
    cx = W * (-0.3 + 1.6 * a); cy = H * 0.35
    d = np.sqrt(((xx - cx) / (W * 0.7)) ** 2 + ((yy - cy) / (H * 0.6)) ** 2)
    m = np.clip(1 - d, 0, 1) ** 1.5 * math.sin(math.pi * a) * 0.95
    col = np.array([255, 170, 90], np.float32) / 255
    x = np.asarray(im, np.float32) / 255
    x = 1 - (1 - x) * (1 - m[..., None] * col)
    return Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))

rng = np.random.default_rng(5)
GRAIN = [rng.normal(0, 4, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
def grain(im, k):
    g = GRAIN[k % 6].repeat(2, 0).repeat(2, 1)
    return Image.fromarray(np.clip(np.asarray(im, np.float32) + g, 0, 255).astype(np.uint8))

if TEST:
    tiles = []
    for s in SHOTS:
        c = Clip(s["v"], s["ss"] + 0.5, s["g"]); fr = c.frame(0); c.p.kill()
        tiles.append(fr.resize((270, 480)))
    sheet = Image.new("RGB", (270 * 6, 480)); [sheet.paste(t, (i * 270, 0)) for i, t in enumerate(tiles)]
    sheet.save(os.path.join(TMP, "kv", "grade_test.jpg"), quality=85); print("test ok"); sys.exit()

texts = [
    T(0.25, 2.3, "into the", SERIF_I, 120, .2, "rise"),
    T(0.45, 2.3, "BACKWATERS", ANTON, 210, .275, "rise", track_k=.04),
    T(2.75, 4.85, "POOVAR  ·  KERALA", MONT, 44, .8, "rise", fill=SAND, track_k=.3),
    T(5.3, 7.35, "lost in the mangroves", SERIF_I, 100, .8, "rise"),
    T(10.25, 12.35, "slow days,", SERIF_I, 110, .76, "rise"),
    T(10.45, 12.35, "golden water", SERIF_I, 110, .825, "rise", fill=PEACH),
    T(12.75, 14.9, "God's own country", SERIF_I, 120, .76, "rise", fill=PEACH),
    T(13.0, 14.9, "KERALA", MONT, 48, .83, "rise", fill=SAND, track_k=.5),
]

SPANS = [(tx.t0, tx.t1, tx.y) for tx in texts]
def tx_act(t, a, b):
    return ve.ease(min(1, (t - a + 0.2) / 0.5, (b + 0.2 - t) / 0.4)) if a - 0.2 <= t <= b + 0.2 else 0
def band(c, w, peak):
    yv = np.linspace(0, 1, H)
    return (np.exp(-((yv - c) / w) ** 2) * peak)[:, None, None].astype(np.float32)
SCRIM_T = band(0.24, 0.13, 0.5)
SCRIM_B = band(0.8, 0.12, 0.48)

# ---------- music: generated beat + whooshes on every transition ----------
DUR = CUTS[-1]
wav = os.path.join(TMP, "kerala_story.wav")
ve.music(wav, DUR, [[("A", 2), ("C#", 3), ("E", 3)], [("F#", 2), ("A", 2), ("C#", 3)],
                    [("D", 3), ("F#", 3), ("A", 3)], [("E", 3), ("G#", 3), ("B", 3)]] * 2, BPM, kick=True)
with wave.open(wav) as w: sr = w.getframerate(); au = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32767
nr = np.random.default_rng(1)
for c in CUTS[1:-1]:
    n = int(0.45 * sr); x = np.linspace(0, 1, n)
    noise = nr.normal(0, 1, n); noise = np.convolve(noise, np.ones(12) / 12, "same")  # soft low-passed noise
    env = np.sin(np.pi * x) ** 2
    s0 = int((c - 0.3) * sr); seg = noise * env * 0.22
    au[s0:s0 + n, 0] += seg[: len(au) - s0]; au[s0:s0 + n, 1] += np.roll(seg, 30)[: len(au) - s0]
au = np.clip(au / max(1, np.abs(au).max() / 0.9), -1, 1)
with wave.open(wav, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((au * 32767).astype(np.int16).tobytes())

# ---------- render ----------
silent = os.path.join(OUT, "kerala_backwaters_story_no_music_for_instagram.mp4")
final = os.path.join(OUT, "kerala_backwaters_story.mp4")
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
clips = [None] * 6
def shot_frame(i, t):
    s = SHOTS[i]
    if clips[i] is None: clips[i] = Clip(s["v"], s["ss"], s["g"])
    lt = t - CUTS[i]
    fr = clips[i].frame(2 * s["sp"](lt))
    e = ve.ease((lt + XF / 2) / (BAR + XF))
    return zoom(fr, s["z"][0] + (s["z"][1] - s["z"][0]) * e)

N = int(DUR * FPS); beat = 60 / BPM; checks = {int(N * f) for f in (.05, .19, .36, .5, .7, .9)}
for k in range(N):
    t = k / FPS
    # inside a transition?
    tr = next((j for j in range(1, 6) if abs(t - CUTS[j]) < XF / 2), None)
    if tr is None:
        i = max(j for j in range(6) if CUTS[j] <= t)
        fr = shot_frame(i, t)
    else:
        a = (t - (CUTS[tr] - XF / 2)) / XF; kind = TRANS[tr - 1]
        A, B = shot_frame(tr - 1, t), shot_frame(tr, t)
        if kind == "zoom":   # punch through: outgoing zooms in, incoming settles from big
            fr = zoom_blur(A, 1 + 0.6 * a ** 2, a) if a < 0.5 else zoom_blur(B, 1 + 0.6 * (1 - a) ** 2, 1 - a)
        elif kind == "whip":  # whip pan left
            off = ve.ease(a); comb = Image.new("RGB", (W, H)); x = int(-W * off)
            comb.paste(A, (x, 0)); comb.paste(B, (x + W, 0))
            fr = hblur(comb, math.sin(math.pi * a))
        else:                 # light leak cross-dissolve
            fr = leak(Image.blend(A, B, ve.ease(a)), a)
    # beat pulse: tiny punch on every beat
    ph = (t % beat) / beat
    fr = zoom(fr, 1 + 0.018 * math.exp(-ph * 8))
    fr = grain(fr, k)
    # soft dark scrim behind whichever text band is on screen, so titles always read
    act_top = max((tx_act(t, a, b) for a, b, y in SPANS if y < .5), default=0)
    act_bot = max((tx_act(t, a, b) for a, b, y in SPANS if y >= .5), default=0)
    if act_top or act_bot:
        x = np.asarray(fr, np.float32)
        fr = Image.fromarray((x * (1 - act_top * SCRIM_T - act_bot * SCRIM_B)).astype(np.uint8))
    fr = fr.convert("RGBA")
    for tx in texts: tx.draw(fr, t)
    rgb = fr.convert("RGB")
    enc.stdin.write(rgb.tobytes())
    if k in checks: rgb.resize((360, 640)).save(os.path.join(TMP, "kv", f"chk_{k:03d}.jpg"), quality=82)
    if k % 30 == 0: print("frame", k, "/", N, flush=True)
enc.stdin.close(); enc.wait()
for c in clips:
    if c: c.p.kill()
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
os.remove(wav)
print("done")
