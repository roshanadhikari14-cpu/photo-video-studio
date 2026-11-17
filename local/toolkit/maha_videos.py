import os, sys, subprocess
SRC = r"C:\Users\MY PC\Video Editing Claude\Mahabalipuram"
os.environ["VE_BASE"] = os.path.join(SRC, "edited")
import numpy as np
from PIL import Image
import video_engine as ve
from video_engine import S, T, ANTON, SERIF_I, MONT, MONO, SAND, PEACH, W, H, FPS

ve.OUT = os.path.join(SRC, "edited", "videos"); os.makedirs(ve.OUT, exist_ok=True)
ve.ONLY = sys.argv[1:]

# colour grade for the phone clips: warmer, punchier, a little crisper
VGRADE = "eq=contrast=1.08:saturation=1.28:gamma=0.96,colorbalance=rs=0.03:bs=-0.05:rm=0.03:bm=-0.04:rh=0.02:bh=-0.03,unsharp=5:5:0.5"

class Clip:
    def __init__(self, name, ss, speed):
        vf = f"setpts=PTS/{speed},fps={FPS},scale={W}:{H}:flags=lanczos,{VGRADE}"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", os.path.join(SRC, name), "-vf", vf,
                                   "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = Image.frombytes("RGB", (W, H), b)
        return self.last  # hold the last frame if the clip runs short

_cam = ve.camera
def camera(shot, lt):
    if "v" not in shot:
        return _cam(shot, lt)
    if "_clip" not in shot:
        shot["_clip"] = Clip(shot["v"], shot.get("ss", 0), shot.get("speed", 1))
    fr = shot["_clip"].next()
    e = ve.ease(lt / shot["d"])
    s = ve.lerp(shot.get("s0", 1), shot.get("s1", 1), e)
    if s != 1:
        cw, ch = W * s, H * s
        cx = W * shot.get("x", .5); cy = H * shot.get("y", .5)
        cx = min(max(cx, cw / 2), W - cw / 2); cy = min(max(cy, ch / 2), H - ch / 2)
        fr = fr.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    return fr
ve.camera = camera

# graded photo numbers (edited/photos/NN_*.jpg)
SHORE, NANDI, RATHAS, RATHA, ELEPHANT, HILLVIEW, SUNSET_TOWN, GOLDEN = 1, 2, 5, 6, 7, 8, 9, 10
LH_SUNSET, LIGHTHOUSE, BB, BB_GLOW, BB_BAL, BB_DUSK, PENANCE, BEACH = 11, 12, 15, 16, 17, 18, 19, 21

# 1 - the lighthouse sunset clip, graded, slow push in, titles
ve.render("01_sunset_from_the_lighthouse", [
    S(None, 16.0, v="IMG_7978.MOV", s0=1.0, s1=0.9, y=0.55),
], [
    T(.5, 4.2, "sunset from the", SERIF_I, 110, .2, "rise"),
    T(.8, 4.2, "LIGHTHOUSE", ANTON, 200, .275, "rise", track_k=.04),
    T(5.5, 9.5, "MAMALLAPURAM · TAMIL NADU", MONT, 40, .8, "rise", fill=SAND, track_k=.25),
    T(11.0, 15.6, "golden hour,", SERIF_I, 120, .76, "rise"),
    T(11.4, 15.6, "always worth it", SERIF_I, 120, .83, "rise", fill=PEACH),
], xf=0, chords=[[("E", 3), ("G#", 3), ("B", 3)], [("C#", 3), ("E", 3), ("G#", 3)], [("A", 2), ("C#", 3), ("E", 3)], [("B", 2), ("D#", 3), ("F#", 3)]], bpm=66)

# 2 - trip reel: rathas clip + photo moments + sped-up sunset clip
b = 60 / 88 * 2
ve.render("02_mahabalipuram_reel", [
    S(None, 3.2, v="IMG_7960.MOV", s0=1, s1=.92),
    S(SHORE, b, x0=.42, x1=.5, s0=.9, s1=.8, y0=.42, y1=.42),
    S(ELEPHANT, b, x0=.4, x1=.5, s0=.85, s1=.95, y0=.55, y1=.55),
    S(LIGHTHOUSE, b, x0=.5, x1=.5, y0=.5, y1=.4, s0=1, s1=.85),
    S(BB_BAL, b, x0=.55, x1=.6, s0=1, s1=.88),
    S(PENANCE, b, x0=.35, x1=.5, s0=.95, s1=.9),
    S(None, 4.6, v="IMG_7978.MOV", ss=7.0, speed=2.0, s0=1, s1=.92),
], [
    T(.3, 2.9, "MAHABALIPURAM", ANTON, 160, .7, "pop", track_k=.02),
    T(.6, 2.9, "STORIES IN STONE", MONT, 40, .775, "rise", fill=SAND, track_k=.3),
    T(3.1, 4.4, "shore temple", SERIF_I, 120, .8, "rise"),
    T(4.5, 5.75, "rathas", SERIF_I, 120, .8, "rise"),
    T(5.85, 7.1, "lighthouse", SERIF_I, 120, .8, "rise"),
    T(7.2, 8.45, "butter ball", SERIF_I, 120, .8, "rise"),
    T(8.55, 9.8, "Arjuna's Penance", SERIF_I, 110, .8, "rise"),
    T(10.2, 14.0, "& a golden sunset", SERIF_I, 120, .78, "rise", fill=PEACH),
    T(10.6, 14.0, "TAMIL NADU", MONT, 42, .85, "rise", fill=SAND, track_k=.3),
], xf=.18, chords=[[("D", 3), ("F#", 3), ("A", 3)], [("B", 2), ("D", 3), ("F#", 3)], [("G", 2), ("B", 2), ("D", 3)], [("A", 2), ("C#", 3), ("E", 3)]] * 2, bpm=88, kick=True, flash=True)

# 3 - butter ball at golden hour (photos)
ve.render("03_butter_ball_golden_hour", [
    S(BB, 3.6, x0=.35, x1=.45, s0=.95, s1=.85, y0=.45, y1=.45),
    S(BB_GLOW, 3.4, x0=.6, x1=.45, s0=.9, s1=.9),
    S(BB_BAL, 3.4, x0=.5, x1=.6, s0=1, s1=.86),
    S(BB_DUSK, 3.6, x0=.5, x1=.5, y0=.45, y1=.45, s0=.8, s1=1),
], [
    T(.4, 3.3, "Krishna's", SERIF_I, 130, .2, "rise"),
    T(.7, 3.3, "BUTTER BALL", ANTON, 190, .275, "rise", track_k=.03),
    T(3.6, 6.3, "defying gravity", SERIF_I, 120, .8, "rise"),
    T(6.7, 9.3, "under a golden sky", SERIF_I, 110, .8, "rise", fill=PEACH),
    T(9.7, 12.4, "still not rolling", SERIF_I, 120, .78, "rise"),
    T(10.1, 12.4, "MAHABALIPURAM", MONT, 40, .845, "rise", fill=SAND, track_k=.3),
], xf=.5, chords=[[("F", 3), ("A", 3), ("C", 4)], [("D", 3), ("F", 3), ("A", 3)], [("A#", 2), ("D", 3), ("F", 3)], [("C", 3), ("E", 3), ("G", 3)]], bpm=72)

# 4 - temple trail: shore temple + rathas clip + photos
ve.render("04_temple_trail", [
    S(SHORE, 3.4, x0=.4, x1=.55, s0=.95, s1=.85, y0=.42, y1=.42),
    S(NANDI, 3.0, x0=.55, x1=.4, s0=.9, s1=.9, y0=.5, y1=.5),
    S(None, 3.2, v="IMG_7960.MOV", s0=.95, s1=1),
    S(ELEPHANT, 3.4, x0=.45, x1=.45, y0=.6, y1=.5, s0=.8, s1=1),
], [
    T(.4, 3.1, "temple trail", SERIF_I, 140, .2, "rise"),
    T(.7, 3.1, "MAHABALIPURAM", MONT, 42, .26, "rise", fill=SAND, track_k=.3),
    T(3.3, 5.9, "Shore Temple, 8th century", SERIF_I, 92, .8, "rise"),
    T(6.2, 8.7, "the Pancha Rathas", SERIF_I, 110, .8, "rise"),
    T(9.0, 11.6, "carved from single rocks", SERIF_I, 96, .78, "rise", fill=PEACH),
    T(9.4, 11.6, "UNESCO WORLD HERITAGE", MONT, 38, .845, "rise", fill=SAND, track_k=.25),
], xf=.5, chords=[[("A", 2), ("C", 3), ("E", 3)], [("F", 2), ("A", 2), ("C", 3)], [("C", 3), ("E", 3), ("G", 3)], [("G", 2), ("B", 2), ("D", 3)]], bpm=70)
