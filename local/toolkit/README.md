# Edit toolkit (reference scripts)

These are the scripts that produced the Kerala, Mahabalipuram and Chikkamagaluru edit packages.
They are REFERENCE CODE: copy the helpers you need into your own script inside the request folder
(paths at the top of each file point at old trips, so do not run them as-is).

| File | What to borrow |
|---|---|
| `kerala_edit.py` | Photo grade (`grade`), `fit` crop, typography (`draw_text`, `fit_font`, `gradient` scrims), post + story builder (`post`, `Y()` safe zone for stories), collages (`place`, `collage`, polaroid / film strip / magazine layouts), `manifest.json` writing |
| `maha_edit.py` | Stronger grade with dehaze, clarity, sky tint and colour wash; DAY / SUNSET / GOLDEN / MOODY presets |
| `cine_grade.py` | Per-frame cinematic grade for video (dehaze, S-curve, vibrance, teal/orange, vignette) |
| `video_engine.py` | Photo/video reel engine: Ken Burns camera, animated text (`T`), generated royalty-free music (`music`), crossfade render |
| `shorts.py` | Five 12-14 s photo shorts built with the engine |
| `maha_videos.py` | Editing phone video clips with the engine (graded clips + titles + photo moments) |
| `kerala_story.py` | 15 s story video from clips: beat cuts, zoom / whip / light-leak transitions, speed ramps, grain, text scrims, music + whooshes |
| `preety_flicker.py` | Trend-reel flicker cut between two clips |

Fonts: `C:\Users\MY PC\.claude\skills\effects\fonts` (Anton, Playfair Display + Italic, Montserrat, Permanent Marker, Space Mono).
Python: `python` (has PIL + numpy). Video: `ffmpeg` / `ffprobe`.

## iPhone HEIC photos

`pillow-heif` is installed: `import pillow_heif; pillow_heif.register_heif_opener()` and then `PIL.Image.open("x.heic")` works (apply `ImageOps.exif_transpose`).
