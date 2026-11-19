"""Build the CampusShield final report: report/report.md -> DOCX (editable) -> PDF (Word).

    python report/build_report.py            # DOCX + PDF
    python report/build_report.py --no-pdf   # DOCX only

Markdown subset: # / ## / ### headings, paragraphs, - bullets, 1. numbered lists,
pipe tables (a line 'Table: caption' just before the table), ```code``` blocks,
![caption](path) images (optional {width=12} in cm), **bold**, *italic*, `code`.

Directives (HTML comments, one per line):
  <!-- PAGEBREAK -->
  <!-- EXCERPT path [first-last] -->           real output copied from an evidence file
  <!-- KALI file [regex] [maxlines] -->        Kali output if evidence/kali/<file> exists, else a PENDING box
  <!-- KALIIMG file caption -->                Kali screenshot if it exists, else a PENDING note
  <!-- IFKALI --> ... <!-- ELSEKALI --> ... <!-- ENDKALI -->   text that depends on the Kali run
The token {{K}} becomes '' when Kali evidence exists, otherwise ' (Kali run pending)'.
"""
import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "report" / "report.md"
OUT_DOCX = ROOT / "report" / "CampusShield_Final_Report.docx"
OUT_PDF = ROOT / "report" / "CampusShield_Final_Report.pdf"
KALI = ROOT / "evidence" / "kali"
HAVE_KALI = (KALI / "SUMMARY.txt").exists()
NAVY = RGBColor(0x1F, 0x4E, 0x79)


# ----------------------------------------------------------------- low-level helpers
def shade(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def add_runs(par, text, size=None, color=None):
    """Inline **bold**, *italic* and `code`."""
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**"):
            run = par.add_run(part[2:-2]); run.bold = True
        elif part.startswith("`"):
            run = par.add_run(part[1:-1]); run.font.name = "Consolas"; run.font.size = Pt(9)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = par.add_run(part[1:-1]); run.italic = True
        else:
            run = par.add_run(part)
        if size and not part.startswith("`"):
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color


def code_box(doc, lines, title=None, fill="F3F5F8", border="C8CED8", size=7.5):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    shade(cell, fill)
    tbl_pr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:color"), border)
        borders.append(el)
    tbl_pr.append(borders)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    if title:
        r = p.add_run(title + "\n"); r.bold = True; r.font.size = Pt(8); r.font.color.rgb = NAVY
    for i, line in enumerate(lines):
        r = p.add_run(line.rstrip("\n") + ("\n" if i < len(lines) - 1 else ""))
        r.font.name = "Consolas"; r.font.size = Pt(size)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def pending_box(doc, text):
    code_box(doc, [text], title="PENDING - real Kali evidence not yet generated", fill="FFF4CE", border="E6C84F", size=8.5)


class Counter:
    fig = 0
    tab = 0


def caption(doc, kind, text):
    if kind == "Figure":
        Counter.fig += 1; n = Counter.fig
    else:
        Counter.tab += 1; n = Counter.tab
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if kind == "Figure" else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(f"{kind} {n}. "); r.bold = True; r.font.size = Pt(9); r.font.color.rgb = NAVY
    add_runs(p, text, size=9)
    p.paragraph_format.space_after = Pt(8 if kind == "Figure" else 3)
    p.paragraph_format.keep_with_next = kind == "Table"


def image(doc, path, cap, width_cm=16.0):
    full = ROOT / path
    if not full.exists():
        pending_box(doc, f"image missing: {path}")
        return
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(full), width=Cm(width_cm))
    caption(doc, "Figure", cap)


def table(doc, rows, cap):
    if cap:
        caption(doc, "Table", cap)
    header, body = rows[0], rows[1:]
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; shade(c, "DCE6F1")
        p = c.paragraphs[0]; add_runs(p, h, size=8.5)
        for r in p.runs:
            r.bold = True
    for row in body:
        cells = t.add_row().cells
        for i, v in enumerate(row[:len(header)]):
            add_runs(cells[i].paragraphs[0], v, size=8.5)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def excerpt(doc, spec):
    parts = spec.split()
    path = ROOT / parts[0]
    if not path.exists():
        pending_box(doc, f"evidence file missing: {parts[0]}")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(parts) > 1 and "-" in parts[1]:
        a, b = (int(x) for x in parts[1].split("-"))
        lines = lines[a - 1:b]
    code_box(doc, [ln[:130] for ln in lines], title=f"Real output - {parts[0]}")


def kali(doc, spec):
    m = re.match(r"(\S+)(?:\s+/(.*)/)?(?:\s+(\d+))?\s*$", spec)
    fname, regex, maxl = m.group(1), m.group(2), int(m.group(3) or 45)
    path = KALI / fname
    if not path.exists():
        pending_box(doc, f"Run 'sudo bash kali/run_kali_lab.sh' in the Kali VM, then rebuild this report. "
                         f"This box will be replaced by real output from evidence/kali/{fname}.")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if regex:
        lines = [ln for ln in lines if re.search(regex, ln)]
    if len(lines) > maxl:
        lines = lines[:maxl] + [f"... ({len(lines) - maxl} more lines in evidence/kali/{fname})"]
    code_box(doc, [ln[:130] for ln in lines], title=f"Real Kali output - evidence/kali/{fname}")


# ----------------------------------------------------------------- document setup
def setup(doc):
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.12
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        h = doc.styles[name]
        h.font.name = "Calibri"; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = NAVY
        h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        h.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
    # page numbers in the footer
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("BCS303 CampusShield - page "); r.font.size = Pt(8)
    for code in ("begin", None, "end"):
        if code is None:
            instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = "PAGE"
            fp.add_run()._r.append(instr)
        else:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), code)
            fp.add_run()._r.append(f)


def title_page(doc):
    def line(text, size, bold=False, color=None, after=6):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold
        if color:
            r.font.color.rgb = color
        p.paragraph_format.space_after = Pt(after)
    line("Canadian University Dubai", 18, True, NAVY, 2)
    line("Faculty of Engineering, Applied Sciences, and Technology", 12, after=40)
    line("BCS303 - Security Principles and Practices", 14, True)
    line("Lab Project Report", 12, after=36)
    line("CampusShield", 30, True, NAVY, 2)
    line("Cybersecurity Defence Project", 16, after=36)
    t = doc.add_table(rows=1, cols=2); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(("Name of student", "Student ID")):
        c = t.rows[0].cells[i]; shade(c, "DCE6F1"); c.paragraphs[0].add_run(h).bold = True
    for name, sid in (("Zuhair Halawa", "20230002902"), ("Ilyass Elmoussaoui", "20240005481")):
        cells = t.add_row().cells
        cells[0].paragraphs[0].add_run(name); cells[1].paragraphs[0].add_run(sid)
    doc.add_paragraph().paragraph_format.space_after = Pt(30)
    line("Instructors: Dr. Mehak Khurana & Mr. Ahmed Seyam", 11)
    line("Date of submission: 20 November 2026", 11)
    line("Source code and evidence: github.com/zuhairhalawa/BCS303-CampusShield (private repository)", 9, after=4)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    # table of contents (Word fills it in when the PDF is exported)
    h = doc.add_paragraph("Contents", style="Heading 1"); h.paragraph_format.keep_with_next = True
    p = doc.add_paragraph()
    for code, text in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None), ("end", None)):
        if code is None:
            instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = text
            p.add_run()._r.append(instr)
        else:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), code)
            p.add_run()._r.append(f)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ----------------------------------------------------------------- markdown walker
def preprocess(text):
    text = text.replace("{{K}}", "" if HAVE_KALI else " (Kali run pending)")
    pattern = re.compile(r"<!-- IFKALI -->(.*?)<!-- ELSEKALI -->(.*?)<!-- ENDKALI -->", re.S)
    return pattern.sub(lambda m: m.group(1) if HAVE_KALI else m.group(2), text)


def build():
    doc = Document()
    setup(doc)
    title_page(doc)
    lines = preprocess(SRC.read_text(encoding="utf-8")).splitlines()
    i, para, pending_cap = 0, [], None
    state = {}

    def flush():
        if para:
            p = doc.add_paragraph(); add_runs(p, " ".join(para)); para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):
            flush(); block = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            code_box(doc, block); i += 1; continue
        if s.startswith("<!--"):
            flush()
            m = re.match(r"<!--\s*(\w+)\s*(.*?)\s*-->", s)
            kind, arg = (m.group(1), m.group(2)) if m else ("", "")
            if kind == "PAGEBREAK":
                state["break"] = True        # applied to the next heading (avoids blank pages)
            elif kind == "EXCERPT":
                excerpt(doc, arg)
            elif kind == "KALI":
                kali(doc, arg)
            elif kind == "KALIIMG":
                fname, _, cap = arg.partition(" ")
                if (KALI / fname).exists():
                    image(doc, f"evidence/kali/{fname}", cap, 16)
                else:
                    pending_box(doc, f"Screenshot to add: evidence/kali/{fname} - {cap}")
            i += 1; continue
        if s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            h = doc.add_heading(s[level:].strip(), level=min(level, 3))
            if state.pop("break", False):
                h.paragraph_format.page_break_before = True
            i += 1; continue
        if s.startswith("Table:"):
            flush(); pending_cap = s[6:].strip(); i += 1; continue
        if s.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            table(doc, rows, pending_cap); pending_cap = None; continue
        m = re.match(r"!\[(.*?)\]\((.*?)\)(\{width=([\d.]+)\})?", s)
        if m:
            flush(); image(doc, m.group(2), m.group(1), float(m.group(4) or 16)); i += 1; continue
        m = re.match(r"(- |\d+\. )(.*)", s)
        if m:
            flush()
            if m.group(1) == "- ":
                p = doc.add_paragraph(style="List Bullet"); add_runs(p, m.group(2))
            else:   # literal numbers: Word's auto-numbering would continue across lists
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.75)
                p.paragraph_format.first_line_indent = Cm(-0.75)
                add_runs(p, m.group(1) + " " + m.group(2))
            p.paragraph_format.space_after = Pt(2)
            i += 1; continue
        if not s:
            flush(); i += 1; continue
        para.append(s); i += 1
    flush()
    doc.save(OUT_DOCX)
    print(f"DOCX: {OUT_DOCX.relative_to(ROOT)}  (figures {Counter.fig}, tables {Counter.tab}, Kali evidence: {HAVE_KALI})")


def export_pdf():
    """Use Microsoft Word (COM via PowerShell) to refresh the TOC and save a PDF.
    Work in a short temp path because Word dislikes very long paths."""
    tmp = Path(tempfile.mkdtemp(prefix="csr_"))
    d, p = tmp / "r.docx", tmp / "r.pdf"
    shutil.copy(OUT_DOCX, d)
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$doc = $w.Documents.Open('{d}'); $doc.TablesOfContents | ForEach-Object {{ $_.Update() }}; "
          f"$doc.Fields.Update() | Out-Null; $doc.Save(); $doc.SaveAs2('{p}', 17); $doc.Close(); $w.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    shutil.copy(p, OUT_PDF)
    shutil.copy(d, OUT_DOCX)          # keep the version with the filled-in table of contents
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"PDF : {OUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    build()
    if not args.no_pdf:
        export_pdf()
