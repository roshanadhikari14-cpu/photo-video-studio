"""Recreate the reference reel's edit with Preety's clips: both landscape clips rotated 90° clockwise to fill 9:16,
flicking between person (P) and scenery (S) with the exact frame pattern measured from the reference (30 fps)."""
import os, sys, subprocess
import numpy as np
SRC = r"C:\Users\MY PC\Video Editing Claude\Preety Chikkamagaluru\video insta"
OUT = r"C:\Users\MY PC\Video Editing Claude\Preety Chikkamagaluru\edited\reels"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("VE_BASE", r"C:\Users\MY PC\Video Editing Claude\Preety Chikkamagaluru\edited")
import video_engine as ve

W, H, FPS = 1080, 1920, 30
# runs measured from the reference: (clip, frames)
RUNS = [("P", 4), ("S", 4), ("P", 3), ("S", 4), ("P", 3), ("S", 3), ("P", 4), ("S", 3), ("P", 3), ("S", 3), ("P", 3), ("S", 3),
        ("P", 3), ("S", 3), ("P", 3), ("S", 4), ("P", 3), ("S", 3), ("P", 4), ("S", 4), ("P", 3), ("S", 4), ("P", 3), ("S", 5),
        ("P", 4), ("S", 3), ("P", 6), ("S", 7), ("P", 5), ("S", 6), ("P", 7), ("S", 7), ("P", 7), ("S", 6), ("P", 6), ("S", 8),
        ("P", 6), ("S", 7), ("P", 6), ("S", 8), ("P", 6), ("S", 7), ("P", 6), ("S", 7), ("P", 6), ("S", 7), ("P", 6), ("S", 7),
        ("P", 5), ("S", 7), ("P", 6), ("S", 7), ("P", 5), ("S", 7), ("P", 7), ("S", 6), ("P", 6), ("S", 6), ("P", 6), ("S", 7)]
N = sum(n for _, n in RUNS)

# per-clip grades: her clip natural + warm; the hazy hills get dehazed, richer greens and a golden cast
GRADE_P = ("eq=contrast=1.12:saturation=1.25:gamma=0.95:brightness=-0.02,"
           "curves=all='0/0 0.25/0.2 0.5/0.48 0.8/0.83 1/0.98',"
           "colorbalance=rs=0.04:bs=-0.035:rm=0.035:bm=-0.04:rh=0.03:bh=-0.03,unsharp=5:5:0.6")
GRADE_S = ("curves=all='0/0 0.3/0.12 0.6/0.42 0.85/0.70 1/0.88',"
           "eq=contrast=1.22:saturation=1.75:gamma=0.9,"
           "colorbalance=rs=0.08:gs=0.02:bs=-0.08:rm=0.10:gm=-0.01:bm=-0.10:rh=0.18:gh=-0.03:bh=-0.10,unsharp=5:5:0.7")

MODE = sys.argv[1] if len(sys.argv) > 1 else "sideways"
def reader(name, ss, speed, grade, zoom, cx, cy):
    # sideways: rotate the landscape clip 90 degrees clockwise (fills 9:16, like the reference)
    # portrait: stay upright and cut a 9:16 window out of the landscape frame
    zw, zh = (f"iw/{zoom}", f"ih/{zoom}") if MODE == "sideways" else (f"ih*9/16/{zoom}", f"ih/{zoom}")
    crop = f"crop={zw}:{zh}:(iw-{zw})*{cx}:(ih-{zh})*{cy}"
    first = "transpose=1" if MODE == "sideways" else "null"
    vf = f"setpts=PTS/{speed},fps={FPS},{first},{crop},scale={W}:{H}:flags=lanczos,{grade}"
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", os.path.join(SRC, name), "-vf", vf,
                             "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

# her clip only moves forward while it is on screen, so her motion stays continuous across the flicks
from cine_grade import Grade
side = "right" if MODE == "sideways" else "top"   # sideways footage has the sky on the right
gradeP = Grade(W, H, sky_side=side, sky=(1.0, 0.8, 0.62), sky_amt=0.3, contrast=0.4, vib=0.35, black=0.02, white=0.98,
               dehaze=0.45, clarity=0.15, gamma=0.88, warm=0.05, teal=0.04)
gradeS = Grade(W, H, sky_side=side, sky=(1.0, 0.72, 0.5), sky_amt=0.45, contrast=0.45, vib=0.5, black=0.02, white=0.98,
               dehaze=0.85, clarity=0.35)
GRADE_P = GRADE_S = "hqdn3d=2:2:3:3"   # light denoise only; the real grade is done per frame in numpy
if MODE == "sideways":
    P = reader("preety 1.MOV", 1.8, 0.8, GRADE_P, 1.32, 0.62, 0.45)   # close on her: hair flip, smile, second flip
    S = reader("preety 2.MOV", 0.0, 1.0, GRADE_S, 1.4, 0.12, 0.5)     # hills, framed on the land, keeps playing
else:
    P = reader("preety 1.MOV", 1.8, 0.8, GRADE_P, 1.0, 0.47, 0.5)    # full-height 9:16 window on her
    S = reader("preety 2.MOV", 0.0, 1.0, GRADE_S, 1.0, 0.3, 0.5)     # 9:16 window with the trees in front
FS = W * H * 3
lastP = lastS = None

name = "this_and_nothing_else" + ("" if MODE == "sideways" else "_portrait")
silent = os.path.join(OUT, name + "_no_music_for_instagram.mp4")
enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
k = 0
for clip, n in RUNS:
    for _ in range(n):
        bs = S.stdout.read(FS)
        if len(bs) == FS: lastS = gradeS(bs, W, H)
        if clip == "P" or lastP is None:
            bp = P.stdout.read(FS)
            if len(bp) == FS: lastP = gradeP(bp, W, H)
        enc.stdin.write(lastP if clip == "P" else lastS)
        k += 1
enc.stdin.close(); enc.wait(); P.kill(); S.kill()
print("frames", k, "=", round(k / FPS, 2), "s")

# the reel's own song, lined up frame-for-frame with the copied cut pattern
REF = os.path.join(SRC, "gawrieee-15112026-0001.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", REF, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", os.path.join(OUT, name + ".mp4")], check=True)
print("done")
