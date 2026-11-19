"""Collect the Moodle submission into submission/.

    python scripts/make_submission.py

Copies the report PDF/DOCX, the slides (PPTX, plus a PDF export if PowerPoint is
available), screenshots and diagrams, and builds a source ZIP of the last commit
with `git archive` (so git-ignored secrets and local databases are never included).
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ROOT / "submission"


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print("  +", dst.relative_to(ROOT))


def slides_pdf(pptx: Path, out: Path):
    tmp = Path(tempfile.mkdtemp(prefix="css_"))
    shutil.copy(pptx, tmp / "d.pptx")
    ps = (f"$p = New-Object -ComObject PowerPoint.Application; "
          f"$d = $p.Presentations.Open('{tmp / 'd.pptx'}', $true, $false, $false); "
          f"$d.SaveAs('{tmp / 'd.pdf'}', 32); $d.Close(); $p.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=180)
        copy(tmp / "d.pdf", out)
    except Exception as exc:  # PowerPoint not installed - PPTX alone is fine
        print("  (no slides PDF:", exc, ")")
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    if SUB.exists():
        shutil.rmtree(SUB)
    SUB.mkdir()
    print("Building submission/ ...")
    copy(ROOT / "report/CampusShield_Final_Report.pdf", SUB / "CampusShield_Final_Report.pdf")
    copy(ROOT / "report/CampusShield_Final_Report.docx", SUB / "CampusShield_Final_Report.docx")
    copy(ROOT / "presentation/CampusShield_Presentation.pptx", SUB / "CampusShield_Presentation.pptx")
    slides_pdf(ROOT / "presentation/CampusShield_Presentation.pptx", SUB / "CampusShield_Slides.pdf")
    copy(ROOT / "presentation/speaker_script.md", SUB / "Demo_and_Speaker_Script.md")
    for png in sorted((ROOT / "evidence/screenshots").glob("*.png")):
        copy(png, SUB / "img" / png.name)
    for png in sorted((ROOT / "evidence/kali").glob("*.png")) if (ROOT / "evidence/kali").exists() else []:
        copy(png, SUB / "img" / ("kali_" + png.name if not png.name.startswith("kali") else png.name))
    for extra in ("evidence/steganography/cover_vs_stego.png", "evidence/privacy/k_anonymity_before_after.png"):
        copy(ROOT / extra, SUB / "img" / Path(extra).name)
    for png in sorted((ROOT / "diagrams").glob("*.png")):
        copy(png, SUB / "img" / png.name)
    for media in sorted((ROOT / "docs/media").glob("*")):          # README media: renders of Kali output + GIFs
        if media.suffix in (".png", ".gif") and not media.name.startswith("slide-"):
            copy(media, SUB / "img" / media.name)
    zip_path = SUB / "CampusShield_Source.zip"
    subprocess.run(["git", "archive", "--format=zip", "--prefix=BCS303-CampusShield/", "-o", str(zip_path), "HEAD", "--", ".", ":(exclude)submission"],
                   cwd=ROOT, check=True)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print("  +", zip_path.relative_to(ROOT), f"(git archive of commit {head})")
    (SUB / "README.txt").write_text(
        "CampusShield - BCS303 submission\n"
        "Zuhair Halawa 20230002902 | Ilyass Elmoussaoui 20240005481\n\n"
        "CampusShield_Final_Report.pdf   final report (DOCX = editable version)\n"
        "CampusShield_Presentation.pptx  slides with speaker notes (Slides.pdf = PDF copy)\n"
        "Demo_and_Speaker_Script.md      who presents what + live demo steps\n"
        "CampusShield_Source.zip         source code, scripts, synthetic data and evidence\n"
        f"                                (git archive of commit {head})\n"
        "img/                            screenshots, Kali output renders, diagrams and 3 demo GIFs\n\n"
        "Run: pip install -r requirements.txt ; python scripts/init_db.py ; python scripts/run_app.py\n"
        "Kali lab: bash kali/docker/run_lab_container.sh (or sudo bash kali/run_kali_lab.sh in a Kali VM)\n"
        "Real Kali output (Nmap, firewall, permissions, pcaps): evidence/kali/ inside the source ZIP\n",
        encoding="utf-8")
    print("  + submission/README.txt\nDone.")


if __name__ == "__main__":
    main()
