"""Small JPEG previews of every upload (HEIC photos and videos included) for the loading animation.
usage: python preview.py <uploads dir> <out dir>"""
import os, subprocess, sys
from PIL import Image, ImageOps
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for name in sorted(os.listdir(src)):
    p, stem = os.path.join(src, name), os.path.splitext(name)[0]
    dst = os.path.join(out, stem + ".jpg")
    try:
        if name.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv")):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", p, "-frames:v", "1",
                            "-vf", "scale=480:-2", dst], check=True)
            continue
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        im.thumbnail((480, 480))
        im.save(dst, quality=80)
    except Exception as e:  # a preview is optional
        print("skip", name, e)
