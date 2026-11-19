"""Render the hand-written SVG diagrams in diagrams/src/*.html to PNG files.

Uses Playwright with the locally installed Microsoft Edge (no browser download).
Run from the repository root:  python diagrams/render_diagrams.py [name ...]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
NAMES = ["architecture", "lab_network", "cloud_architecture", "attack_defend_verify"]


def main(names):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
        for name in names:
            src = SRC / f"{name}.html"
            if not src.exists():
                print(f"skip {name}: {src} missing")
                continue
            page.goto(src.as_uri())
            out = HERE / f"{name}.png"
            page.locator("svg").first.screenshot(path=str(out))
            print(f"wrote {out.relative_to(HERE.parent)}")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:] or NAMES)
