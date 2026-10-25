# Build the silent explainer video from scripts/video_slides.html: screenshot each slide with headless Edge (1280x720), then join them with
# ffmpeg (fade between slides) into docs/video/radar.mp4, and write a lighter animated GIF docs/video/radar.gif for the README.
# Needs Pillow and imageio-ffmpeg (ships an ffmpeg binary); they are not in requirements.txt because the pipeline does not use them.
# Usage: python -X utf8 scripts/build_video.py [seconds_per_slide]
import os, re, subprocess, sys, tempfile
import imageio_ffmpeg
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "scripts", "video_slides.html")
OUT = os.path.join(ROOT, "docs", "video")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SEC = float(sys.argv[1]) if len(sys.argv) > 1 else 7.0
FADE = 0.5
GIF_MS = 5000

n = len(re.findall(r'<section class="slide"', open(HTML, encoding="utf-8").read()))
os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="radar_video_")
url = "file:///" + HTML.replace(os.sep, "/")
imgs = []
for s in range(1, n + 1):
    png = os.path.join(tmp, f"s{s:02d}.png")
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1280,720",
                    f"--user-data-dir={os.path.join(tmp, 'profile')}", f"--screenshot={png}", f"{url}?s={s}"],
                   check=True, capture_output=True, timeout=60)
    imgs.append(png)
print("slides:", n, "->", tmp)

ff = imageio_ffmpeg.get_ffmpeg_exe()
args = [ff, "-y", "-loglevel", "error"]
for p in imgs:
    args += ["-loop", "1", "-t", str(SEC), "-framerate", "25", "-i", p]
chains = [f"[{i}:v]fade=t=in:st=0:d={FADE},fade=t=out:st={SEC - FADE}:d={FADE},format=yuv420p[v{i}]" for i in range(n)]
graph = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[out]"
mp4 = os.path.join(OUT, "radar.mp4")
subprocess.run(args + ["-filter_complex", graph, "-map", "[out]", "-c:v", "libx264", "-crf", "28", "-preset", "slow",
                       "-movflags", "+faststart", mp4], check=True)

# the GIF holds each slide still (no fades), so it stays small
frames = [Image.open(p).convert("RGB").resize((960, 540), Image.LANCZOS).quantize(colors=64, method=Image.Quantize.MEDIANCUT) for p in imgs]
gif = os.path.join(OUT, "radar.gif")
frames[0].save(gif, save_all=True, append_images=frames[1:], duration=GIF_MS, loop=0, optimize=True)
for f in (mp4, gif):
    print(f, round(os.path.getsize(f) / 1e6, 2), "MB")
