"""Least-significant-bit (LSB) steganography in a locally generated PNG.

The message bits replace the lowest bit of each R, G, B value. A 32-bit header
stores the message length so the extractor knows when to stop.
Run:  python demonstrations/steganography/lsb_stego.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EVID = ROOT / "evidence" / "steganography"
EVID.mkdir(parents=True, exist_ok=True)
LOG = EVID / "stego_output.txt"
lines = []


def say(text=""):
    print(text)
    lines.append(str(text))


def make_cover(path):
    """Draw a simple gradient image with the project name (no downloaded images)."""
    w, h = 400, 260
    img = Image.new("RGB", (w, h))
    px = img.load()
    for x in range(w):
        for y in range(h):
            px[x, y] = (30 + x * 120 // w, 70 + y * 100 // h, 140 + (x + y) * 80 // (w + h))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    d.text((70, 105), "CampusShield", fill=(255, 255, 255), font=font)
    img.save(path)
    return img


def hide(cover, message):
    data = message.encode("utf-8")
    bits = f"{len(data):032b}" + "".join(f"{b:08b}" for b in data)
    img = cover.copy()
    flat = [c for p in img.getdata() for c in p]
    if len(bits) > len(flat):
        raise ValueError("message too long for this image")
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & ~1) | int(bit)
    img.putdata([tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)])
    return img


def reveal(img):
    flat = [c for p in img.convert("RGB").getdata() for c in p]
    length = int("".join(str(v & 1) for v in flat[:32]), 2)
    if length <= 0 or length * 8 + 32 > len(flat):
        raise ValueError(f"no valid hidden message (length header = {length})")
    bits = "".join(str(v & 1) for v in flat[32:32 + length * 8])
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)).decode("utf-8")


cover_path, stego_path = HERE / "cover.png", HERE / "stego.png"
message = "CampusShield lab: the BCS303 demo starts at 10:00 in Lab 2."
cover = make_cover(cover_path)
stego = hide(cover, message)
stego.save(stego_path)

say("=== Hide ===")
say(f"cover image : {cover_path.relative_to(ROOT)} {cover.size[0]}x{cover.size[1]} px")
say(f"message     : {message!r} ({len(message.encode())} bytes = {32 + 8 * len(message.encode())} bits incl. header)")
say(f"stego image : {stego_path.relative_to(ROOT)}")
say(f"file sizes  : cover {cover_path.stat().st_size} bytes, stego {stego_path.stat().st_size} bytes")

say()
say("=== Extract ===")
recovered = reveal(Image.open(stego_path))
say(f"recovered   : {recovered!r}")
say(f"matches     : {recovered == message}")

say()
say("=== How visible is the change? ===")
a, b = list(cover.getdata()), list(Image.open(stego_path).getdata())
changed = sum(1 for p, q in zip(a, b) if p != q)
max_diff = max(abs(x - y) for p, q in zip(a, b) for x, y in zip(p, q))
say(f"pixels changed: {changed} of {len(a)} ({100 * changed / len(a):.2f}%)")
say(f"largest change in any colour channel: {max_diff} (out of 255) - not visible to the eye")

say()
say("=== Limitation 1: lossy re-compression destroys the message ===")
jpeg_path = HERE / "stego_resaved.jpg"
Image.open(stego_path).save(jpeg_path, quality=90)
try:
    out = reveal(Image.open(jpeg_path))
    say(f"after JPEG re-save: {out[:60]!r} -> matches original? {out == message}")
except (ValueError, UnicodeDecodeError) as exc:
    say(f"after JPEG re-save: extraction failed ({type(exc).__name__}: {exc})")

say()
say("=== Limitation 2: hiding is not encryption ===")
say("Anyone who suspects LSB stego can run the same reveal() function and read the text in clear:")
say(f"  third-party extraction -> {reveal(Image.open(stego_path))!r}")
say("To keep the content confidential, encrypt it first (e.g. AES-GCM) and then hide the ciphertext.")

# side-by-side evidence picture: cover | stego | amplified difference
diff = Image.new("RGB", cover.size)
diff.putdata([tuple(255 if x != y else 0 for x, y in zip(p, q)) for p, q in zip(a, b)])
canvas = Image.new("RGB", (cover.size[0] * 3 + 40, cover.size[1] + 40), "white")
for i, (im, label) in enumerate([(cover, "cover.png"), (Image.open(stego_path), "stego.png"),
                                 (diff, "changed bits (white)")]):
    canvas.paste(im, (10 + i * (cover.size[0] + 10), 30))
    ImageDraw.Draw(canvas).text((10 + i * (cover.size[0] + 10), 8), label, fill=(0, 0, 0))
canvas.save(EVID / "cover_vs_stego.png")
say()
say(f"comparison picture saved to {(EVID / 'cover_vs_stego.png').relative_to(ROOT)}")

LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n[saved to {LOG.relative_to(ROOT)}]")
