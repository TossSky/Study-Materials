# -*- coding: utf-8 -*-
"""Собирает экзаменационный PDF настоящим LaTeX (tectonic).
Задание: %TEMP%/tex_job.json = {"out":abs.pdf, "title":.., "subtitle":.., "toc":bool, "blocks":[abs.tex,...]}
Шрифты: <ExamPrep>/fonts (CMU = Computer Modern Unicode, с кириллицей)."""
import os, json, subprocess, shutil

ROOT     = r"c:\Users\vyach\Study-Materials\Semester-4\TeorVer\ExamPrep"
FONTS    = "fonts"  # относительный путь (двоеточие в c:/ ломает fontspec)
TECTONIC = r"C:\Users\vyach\AppData\Local\Temp\tex\tectonic.exe"

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage{fontspec}
\setmainfont{cmunrm.otf}[Path=%s/,
  ItalicFont=cmunti.otf, BoldFont=cmunbx.otf, BoldItalicFont=cmunbi.otf]
\usepackage{amsmath,amssymb}
\usepackage[a4paper,margin=2.1cm]{geometry}
\usepackage{enumitem}
\usepackage{polyglossia}
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setlist{topsep=2pt,itemsep=1pt,parsep=0pt,leftmargin=1.6em}
\linespread{1.04}
\begin{document}
""" % FONTS

def build(job):
    out   = job["out"]
    parts = [PREAMBLE]
    if job.get("title"):
        parts.append(r"\begin{center}{\LARGE\bfseries %s}\par" % job["title"])
        if job.get("subtitle"):
            parts.append(r"\vskip 4pt {\large %s}\par" % job["subtitle"])
        parts.append(r"\end{center}\vskip 10pt")
    if job.get("toc"):
        parts.append(r"\renewcommand{\contentsname}{Содержание}\tableofcontents\newpage")
    for b in job["blocks"]:
        rel = os.path.relpath(b, ROOT).replace("\\", "/") if os.path.isabs(b) else b.replace("\\", "/")
        parts.append(r"\input{%s}" % rel)
        parts.append("")
    parts.append(r"\end{document}")
    tex = "\n".join(parts)

    main_tex = os.path.join(ROOT, "_main.tex")
    open(main_tex, "w", encoding="utf-8").write(tex)
    # tectonic компилирует дважды для toc автоматически? нет — делаем 2 прохода при toc
    passes = 2 if job.get("toc") else 1
    for _ in range(passes):
        r = subprocess.run([TECTONIC, "--keep-logs", "-o", ROOT, main_tex],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
    produced = os.path.join(ROOT, "_main.pdf")
    if not os.path.exists(produced):
        raise RuntimeError("PDF не создан:\n" + (r.stderr or "")[-1500:])
    shutil.move(produced, out)
    return out

def main():
    job = json.load(open(os.path.join(os.environ["TEMP"], "tex_job.json"), encoding="utf-8"))
    try:
        out = build(job)
        print(f"OK  {os.path.basename(out)}  {os.path.getsize(out)/1024:.0f} KB")
    except Exception as e:
        print("FAIL:", e)

if __name__ == "__main__":
    main()
