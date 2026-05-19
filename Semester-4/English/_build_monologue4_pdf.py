"""Generate Monologue 4 PDF matching the official conspectus criteria:

- Active Vocabulary (**bold**)   -> YELLOW highlight + bold (per criteria)
- Linkers (***bold-italic***)    -> GREEN bold italic (per criteria + Mon 3 style)
- Title centered, group + author line below
- 9 numbered paragraphs, justified
"""
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER


BASE = r"c:\GitRepo\Study-Materials\Semester-4\English"
MD_PATH = os.path.join(BASE, "Monologue_4_Program_Design_and_Computer_Languages.md")
PDF_PATH = os.path.join(BASE, "Monologue_4_Program_Design_and_Computer_Languages.pdf")


def md_inline_to_html(text: str) -> str:
    """Convert markdown inline markup to reportlab miniHTML.

    Linkers first (triple-stars), then vocabulary (double-stars).
    """
    # Linkers: ***text*** -> green bold italic
    text = re.sub(
        r"\*\*\*(.+?)\*\*\*",
        lambda m: f'<b><i><font color="#548235">{m.group(1)}</font></i></b>',
        text,
    )
    # Vocabulary: **text** -> yellow highlight + bold (background via <font backColor>)
    text = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: f'<b><font backColor="#FFFF00">{m.group(1)}</font></b>',
        text,
    )
    return text


def build():
    with open(MD_PATH, encoding="utf-8") as f:
        raw = f.read()

    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Monologue on Program Design and Computer Languages",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=black,
    )
    author_style = ParagraphStyle(
        "Author",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    h_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=6,
        textColor=black,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=15,
        spaceAfter=6,
        firstLineIndent=1 * cm,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        alignment=TA_LEFT,
        spaceBefore=14,
        leading=12,
    )

    story = []

    lines = raw.splitlines()
    i = 0
    # Title is the first '# ' line; the next non-empty non-heading line is the author line
    saw_author = False
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.startswith("# "):
            story.append(Paragraph(line[2:].strip(), title_style))
            i += 1
            # consume author line (first non-empty line that isn't a heading)
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and not lines[i].startswith("#") and not lines[i].startswith("---"):
                story.append(Paragraph(lines[i].strip(), author_style))
                saw_author = True
                i += 1
            continue
        elif line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), h_style))
        elif line.startswith("---"):
            i += 1
            legend_lines = []
            while i < len(lines):
                tail = lines[i].strip()
                if tail:
                    legend_lines.append(tail)
                i += 1
            story.append(Paragraph(
                '<b><font backColor="#FFFF00">Yellow = Active Vocabulary</font></b>, '
                '<b><i><font color="#548235">Green/Bold Italic = Linkers</font></i></b>',
                footer_style,
            ))
            for ll in legend_lines:
                story.append(Paragraph(md_inline_to_html(ll), footer_style))
            break
        else:
            story.append(Paragraph(md_inline_to_html(line), body_style))

        i += 1

    doc.build(story)
    print(f"Saved: {PDF_PATH}")


if __name__ == "__main__":
    build()
