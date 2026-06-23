# -*- coding: utf-8 -*-
"""Сборка КОНСПЕКТ_АСВТ.html из .md: тёмная тема + инлайн-SVG схемы (offline, без CDN-схем)."""
import re, subprocess, sys, math
try:
    import markdown
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "markdown"], check=True)
    import markdown

SRC, OUT = "КОНСПЕКТ_АСВТ_экзамен.md", "КОНСПЕКТ_АСВТ.html"

# ───────────────────────── SVG-движок ─────────────────────────
PAL = dict(box="#1b2431", box2="#131a24", text="#e8eef4", muted="#9fb0c0",
           edge="#5d7governs", acc="#46d09a", acc2="#4cc0f0", lblbg="#0f141b", line="#46566a")
PAL["edge"] = "#62748a"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _box(cx, cy, w, h, label, acc, shape):
    lines = label.split("\n"); lh = 15.5
    ty = cy - (len(lines) - 1) * lh / 2 + 4.5
    tsp = "".join(f'<tspan x="{cx:.1f}" y="{ty + i*lh:.1f}">{esc(t)}</tspan>' for i, t in enumerate(lines))
    if shape == "circle":
        r = h / 2
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#bx)" stroke="{acc}" '
                f'stroke-width="1.6" filter="url(#sh)"/><text class="nl" text-anchor="middle">{tsp}</text>')
    x, y = cx - w/2, cy - h/2
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="11" fill="url(#bx)" '
            f'stroke="{acc}" stroke-width="1.5" filter="url(#sh)"/>'
            f'<text class="nl" text-anchor="middle">{tsp}</text>')

def _border(cx, cy, w, h, tx, ty):
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0: return cx, cy
    sx = (w/2) / abs(dx) if dx else 1e9
    sy = (h/2) / abs(dy) if dy else 1e9
    s = min(sx, sy)
    return cx + dx*s, cy + dy*s

def _lbl(mx, my, text):
    w = len(text) * 6.0 + 12
    return (f'<rect x="{mx-w/2:.1f}" y="{my-9:.1f}" width="{w:.1f}" height="18" rx="5" '
            f'fill="{PAL["lblbg"]}" stroke="{PAL["line"]}" stroke-width="1"/>'
            f'<text x="{mx:.1f}" y="{my+4:.1f}" text-anchor="middle" class="el">{esc(text)}</text>')

def _edge(x1, y1, x2, y2, label=None, arrow=True, dash=False, bow=0.0):
    da = ' stroke-dasharray="6 4"' if dash else ''
    mk = ' marker-end="url(#ar)"' if arrow else ''
    if bow:
        mxp, myp = (x1+x2)/2, (y1+y2)/2
        nx, ny = -(y2-y1), (x2-x1); L = math.hypot(nx, ny) or 1
        cxp, cyp = mxp + nx/L*bow, myp + ny/L*bow
        path = f'<path d="M{x1:.1f},{y1:.1f} Q{cxp:.1f},{cyp:.1f} {x2:.1f},{y2:.1f}" fill="none" stroke="{PAL["edge"]}" stroke-width="1.6"{da}{mk}/>'
        lx, ly = cxp, cyp
    else:
        path = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{PAL["edge"]}" stroke-width="1.6"{da}{mk}/>'
        lx, ly = (x1+x2)/2, (y1+y2)/2
    return path + (_lbl(lx, ly, label) if label else "")

def diagram(nodes, edges, ncols, nrows, colw=200, rowh=108, pad=20, title=None):
    th = 26 if title else 0
    W = pad*2 + ncols*colw
    H = pad*2 + nrows*rowh + th
    geo = {}
    for n in nodes:
        nid, label, col, row = n[0], n[1], n[2], n[3]
        shape = n[4] if len(n) > 4 else "rect"
        acc = n[5] if len(n) > 5 else PAL["acc"]
        lines = label.split("\n")
        bw = min(colw - 16, max(86, max(len(l) for l in lines) * 7.0 + 22))
        bh = max(40, 19 + len(lines) * 15.5)
        if shape == "circle": bw = bh = max(bw, bh, 46)
        cx = pad + col*colw + colw/2
        cy = pad + th + row*rowh + rowh/2
        geo[nid] = (cx, cy, bw, bh, label, acc, shape)
    parts = []
    for e in edges:
        a, b = e[0], e[1]
        lbl = e[2] if len(e) > 2 else None
        fl = e[3] if len(e) > 3 else ""
        ca, cb = geo[a], geo[b]
        x1, y1 = _border(ca[0], ca[1], ca[2], ca[3], cb[0], cb[1])
        x2, y2 = _border(cb[0], cb[1], cb[2], cb[3], ca[0], ca[1])
        bow = 34 if "C+" in fl else (-34 if "C-" in fl else 0)
        parts.append(_edge(x1, y1, x2, y2, lbl, arrow="line" not in fl, dash="dash" in fl, bow=bow))
    for nid, g in geo.items():
        parts.append(_box(g[0], g[1], g[2], g[3], g[4], g[5], g[6]))
    if title:
        parts.insert(0, f'<text x="{W/2:.0f}" y="17" text-anchor="middle" class="dt">{esc(title)}</text>')
    defs = ('<defs>'
            f'<linearGradient id="bx" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PAL["box"]}"/>'
            f'<stop offset="1" stop-color="{PAL["box2"]}"/></linearGradient>'
            f'<marker id="ar" markerWidth="9" markerHeight="9" refX="7.5" refY="3" orient="auto">'
            f'<path d="M0,0 L7.5,3 L0,6 Z" fill="{PAL["edge"]}"/></marker>'
            '<filter id="sh" x="-25%" y="-25%" width="150%" height="170%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="2.4" flood-color="#000" flood-opacity="0.5"/></filter></defs>')
    style = ('<style>'
             f'text.nl{{fill:{PAL["text"]};font:600 12.5px "IBM Plex Sans",sans-serif}}'
             f'text.el{{fill:{PAL["muted"]};font:500 10.5px "IBM Plex Sans",sans-serif}}'
             f'text.dt{{fill:{PAL["muted"]};font:600 12px "IBM Plex Sans",sans-serif;letter-spacing:.3px}}'
             '</style>')
    return (f'<div class="fig"><svg viewBox="0 0 {W:.0f} {H:.0f}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" preserveAspectRatio="xMidYMid meet">{defs}{style}{"".join(parts)}</svg></div>')

# ───────────────────────── схемы (ключ = подстрока ASCII-блока) ─────────────────────────
A2 = PAL["acc2"]
D = {}
D["ЦП (CPU)"] = diagram(
    [("CPU","ЦП — УУ + АЛУ",1,0,"rect",A2),("MEM","Память (ОЗУ):\nкоманды + данные",0,1),("IO","Устройства\nввода-вывода",2,1)],
    [("CPU","MEM","адрес / данные / упр"),("CPU","IO","шины")], 3, 2)
D["операнд A ─►"] = diagram(
    [("A","операнд A",0,0),("B","операнд B",0,1),("OP","код операции",0,2),
     ("ALU","АЛУ\n+ − И ИЛИ, сдвиги",1,1,"rect",A2),("R","результат",2,0),("F","флаги Z C S O",2,2)],
    [("A","ALU"),("B","ALU"),("OP","ALU"),("ALU","R"),("ALU","F")], 3, 3)
D["управляющие сигналы на АЛУ"] = diagram(
    [("C","команда",0,0),("T","такты",0,1),("UU","УУ\nдешифратор + автомат",1,0,"rect",A2),
     ("S","упр. сигналы:\nАЛУ · регистры\nпамять · ВВ",2,0)],
    [("C","UU"),("T","UU"),("UU","S")], 3, 2)
D["матрица И"] = diagram(
    [("X","входы\nx1..xn",0,0),("AND","Матрица И\n(конъюнкции)",1,0,"rect",A2),
     ("OR","Матрица ИЛИ\n(сумма)",2,0,"rect",A2),("F","выходы\nf1..fm",3,0)],
    [("X","AND"),("AND","OR","термы"),("OR","F")], 4, 1, colw=170)
D["микропрограммное УУ"] = diagram(
    [("CC","CISC\nкоманда",0,0),("CM","микропрогр.\nУУ",1,0,"rect",A2),("CK","микро-\nкоманды",2,0),("CA","АЛУ",3,0),
     ("RC","RISC\nкоманда",0,1),("RH","аппаратное\nУУ",1,1,"rect",A2),("RA","АЛУ\n(1 такт)",3,1)],
    [("CC","CM"),("CM","CK"),("CK","CA"),("RC","RH"),("RH","RA")], 4, 2, colw=170)
D["[ALU 1]"] = diagram(
    [("F","выборка\nнеск. команд",0,1),("A1","ALU 1",1,0),("A2","ALU 2",1,1),("FP","FPU",1,2),
     ("R",">1 команды\nза такт",2,1,"rect",A2)],
    [("F","A1"),("F","A2"),("F","FP"),("A1","R"),("A2","R"),("FP","R")], 3, 3, colw=170)
D["1 строка (адрес mod N)"] = diagram(
    [("B","блок ОП",0,1,"rect",A2),("Dr","Прямое:\n1 строка (addr mod N)",1,0),
     ("As","Полностью\nассоциативное",1,1),("Ms","Множ.-ассоц.:\nстрока набора (K-way)",1,2)],
    [("B","Dr"),("B","As"),("B","Ms")], 2, 3, colw=240)
D["регистры → L1-кэш"] = diagram(
    [("R","регистры",0,0,"rect",A2),("L1","L1-кэш",0,1),("L2","L2-кэш",0,2),("L3","L3",0,3),
     ("RAM","ОЗУ",0,4),("DC","дисковый кэш",0,5),("HD","магн. диски / RAID",0,6),("OP","оптика, ленты",0,7)],
    [("R","L1","быстрее·дороже"),("L1","L2"),("L2","L3"),("L3","RAM"),("RAM","DC"),("DC","HD"),("HD","OP","больше·дешевле")],
    1, 8, colw=260, rowh=78)
D["RAID0: A1 A2"] = diagram(
    [("R","RAID",0,2,"rect",A2),("R0","RAID 0\nстрайп (скорость)",1,0),("R1","RAID 1\nзеркало",1,1),
     ("R5","RAID 5\nстрайп + чётность",1,2),("R6","RAID 6\n2 чётности",1,3),("R10","RAID 10\nзеркало + страйп",1,4)],
    [("R","R0"),("R","R1"),("R","R5"),("R","R6"),("R","R10")], 2, 5, colw=230, rowh=78)
D["встроены контроллер памяти"] = diagram(
    [("CPU","ЦП\nконтроллер памяти\n+ PCIe + iGPU",1,0,"rect",A2),("GPU","видеокарта",2,1),
     ("PCH","PCH (южный мост):\nUSB · SATA · сеть\nаудио · LPC → BIOS",1,2)],
    [("CPU","GPU","PCIe"),("CPU","PCH","DMI")], 3, 3)
D["рег.данных"] = diagram(
    [("BUS","системная\nшина",0,0),("MVV","МВВ\nрег. данных · состояния\nупр. логика · дешифратор",1,0,"rect",A2),
     ("PU","ПУ\n(датчик / привод)",2,0)],
    [("BUS","MVV"),("MVV","PU")], 3, 1, colw=250)
D["[читать рег.состояния]"] = diagram(
    [("S","читать регистр\nсостояния",0,0),("Q","ПУ готов?",1,0,"rect",A2),("X","обмен данными",2,0)],
    [("S","Q"),("Q","X","да"),("Q","S","нет","C+")], 3, 1, colw=190)
D["[IRQ от ПУ]"] = diagram(
    [("W","ЦП занят\nсвоим делом",0,0),("SV","сохранить\nсостояние",1,0),("H","обработчик\n(по вектору)",2,0,"rect",A2),
     ("EX","обмен",3,0),("RET","возврат",4,0)],
    [("W","SV","IRQ от ПУ"),("SV","H"),("H","EX"),("EX","RET")], 5, 1, colw=160)
D["запрос DMA"] = diagram(
    [("CPU","ЦП",0,0),("DMAC","КПДП\n(DMAC)",1,0,"rect",A2),("PU","ПУ",2,0),("MEM","Память",1,1)],
    [("CPU","DMAC"),("DMAC","PU","запрос DMA"),("DMAC","MEM"),("PU","MEM","обмен минуя ЦП","dash")], 3, 2)
D["SISD: 1 команда → 1 данные"] = diagram(
    [("SISD","SISD\n1 команда → 1 поток",0,0,"rect",A2),("SIMD","SIMD\n1 команда → много данных",1,0,"rect",A2),
     ("MISD","MISD\nмного команд → 1 данные",0,1),("MIMD","MIMD\nмного команд → много",1,1,"rect",A2)],
    [], 2, 2, colw=240)
D["общая шина"] = diagram(
    [("P1","ЦП",0,0),("P2","ЦП",1,0),("P3","ЦП",2,0),("BUS","общая шина",1,1,"rect",A2),
     ("M","общая память\n(время доступа одинаково)",1,2)],
    [("P1","BUS","","line"),("P2","BUS","","line"),("P3","BUS","","line"),("BUS","M","","line")], 3, 3)
D["обмен только сообщениями"] = diagram(
    [("N1","ЦП + память",0,0),("N2","ЦП + память",1,0),("N3","ЦП + память",2,0)],
    [("N1","N2","сеть","line"),("N2","N3","сеть","line")], 3, 1)
D["своя память — быстро, чужая — медленно"] = diagram(
    [("C0","ЦП",0,0),("L0","лок. память",0,1),("SW","сеть / коммутатор\n(общее адр. простр.)",1,0,"rect",A2),
     ("C1","ЦП",2,0),("M1","лок. память",2,1)],
    [("C0","L0","","line"),("C1","M1","","line"),("C0","SW","своя — быстро"),("C1","SW","чужая — медленно")], 3, 2)
D["общий УУ (одна команда всем)"] = diagram(
    [("UU","общий УУ\n(одна команда всем)",1.5,0,"rect",A2),("P1","ПЭ + память",0,1),("P2","ПЭ + память",1,1),
     ("P3","ПЭ + память",2,1),("P4","ПЭ + память",3,1)],
    [("UU","P1"),("UU","P2"),("UU","P3"),("UU","P4")], 4, 2, colw=170)
D["сравнение со ВСЕМИ ячейками сразу"] = diagram(
    [("K","признак\nпоиска",0,0),("C","сравнение со ВСЕМИ\nячейками (по содержимому)",1,0,"rect",A2),
     ("R","совпавшие\nячейки",2,0)],
    [("K","C"),("C","R")], 3, 1, colw=235)
D["ритмичный поток"] = diagram(
    [("D","данные",0,0),("P1","ПЭ",1,0,"rect",A2),("P2","ПЭ",2,0,"rect",A2),("P3","ПЭ",3,0,"rect",A2),("R","результат",4,0)],
    [("D","P1"),("P1","P2"),("P2","P3"),("P3","R")], 5, 1, colw=130)
D["[вект.ЦП]"] = diagram(
    [("V1","вект. ЦП",0,0,"rect",A2),("V2","вект. ЦП",1,0,"rect",A2),("V3","вект. ЦП",2,0,"rect",A2),
     ("SW","коммутатор\n(кроссбар)",1,1),("M","разделяемая\nпамять",1,2)],
    [("V1","SW","","line"),("V2","SW","","line"),("V3","SW","","line"),("SW","M","","line")], 3, 3)
D["каждый = ЦП+память"] = diagram(
    [("U1","узел:\nЦП + память",0,0),("U2","узел:\nЦП + память",1,0),("U3","узел:\nЦП + память",2,0),
     ("NET","высокоскоростная сеть",1,1,"rect",A2)],
    [("U1","NET","","line"),("U2","NET","","line"),("U3","NET","","line")], 3, 2)
D["каждый узел — целый компьютер"] = diagram(
    [("N1","узел —\nцелый ПК",0,0),("N2","узел —\nцелый ПК",1,0),("N3","узел —\nцелый ПК",2,0),
     ("SW","сеть / коммутатор (switch)",1,1,"rect",A2)],
    [("N1","SW","","line"),("N2","SW","","line"),("N3","SW","","line")], 3, 2)
D["узлы срабатывают, когда пришли операнды"] = diagram(
    [("a","a",0,0),("b","b",1,0),("c","c",2,0),("d","d",3,0),
     ("plus","+",0.5,1,"circle",A2),("mul","×",2.5,1,"circle",A2),("minus","−",1.5,2,"circle",A2),("R","результат",1.5,3)],
    [("a","plus"),("b","plus"),("c","mul"),("d","mul"),("plus","minus"),("mul","minus"),("minus","R")], 4, 4, colw=150)
D["P-ядро P-ядро"] = diagram(
    [("P1","P-ядро",0,0,"rect",A2),("P2","P-ядро",1,0,"rect",A2),("E1","E-ядро",2,0),("E2","E-ядро",3,0),("G","iGPU",4,0),
     ("L3","общий кэш L3 (кольцо / mesh)",2,1),("MC","контроллер памяти + PCIe",2,2)],
    [("P1","L3"),("P2","L3"),("E1","L3"),("E2","L3"),("G","L3"),("L3","MC")], 5, 3, colw=150)
D["Infinity Fabric"] = diagram(
    [("C0","CCD0:\n8 ядер + L3",0,0,"rect",A2),("C1","CCD1:\n8 ядер + L3",2,0,"rect",A2),
     ("IF","Infinity Fabric",1,1),("IOD","I/O-die\nконтр. памяти · PCIe · USB",1,2)],
    [("C0","IF","","line"),("C1","IF","","line"),("IF","IOD","","line")], 3, 3)
# MESI — граф состояний (ромб + кривые рёбра)
D["чтение(miss, есть у других)"] = diagram(
    [("M","M\nModified",1,0,"rect","#e07a8b"),("E","E\nExclusive",0,1,"rect",A2),
     ("S","S\nShared",2,1,"rect",PAL["acc"]),("I","I\nInvalid",1,2,"rect",PAL["muted"])],
    [("I","E","чтение (ни у кого)","C-"),("I","S","чтение (у других)","C+"),
     ("E","M","запись"),("S","M","запись → инвал.","C+"),
     ("M","I","чужая запись"),("M","S","чужое чтение","C-"),("E","I","чужая запись","C-")],
    3, 3, colw=185, rowh=120)

PIPE = "PPLINEPLACEHOLDER"
def pipeline_html():
    st = [("IF","s1"),("ID","s2"),("EX","s3"),("MEM","s4"),("WB","s5")]
    head = "".join(f"<th>{c}</th>" for c in range(1, 10))
    rows = ""
    for i in range(5):
        tds = ""
        for cyc in range(9):
            s = cyc - i
            tds += (f'<td class="pp {st[s][1]}">{st[s][0]}</td>' if 0 <= s < 5 else "<td></td>")
        rows += f"<tr><th>К{i+1}</th>{tds}</tr>"
    return ('<div class="fig"><div class="cap">Конвейер: 1 команда за такт (стадии перекрываются)</div>'
            f'<table class="pipe"><thead><tr><th>такт→</th>{head}</tr></thead><tbody>{rows}</tbody></table>'
            '<div class="cap">IF выборка · ID декод · EX исполнение · MEM память · WB запись</div></div>')

# ───────────────────────── разбор .md ─────────────────────────
src = open(SRC, encoding="utf-8").read()
lines = src.split("\n"); out = []; i = 0
while i < len(lines):
    s = lines[i].strip()
    if s.startswith("```"):
        j = i + 1; buf = []
        while j < len(lines) and lines[j].strip() != "```":
            buf.append(lines[j]); j += 1
        content = "\n".join(buf)
        if "IF=выборка" in content:
            out.append(PIPE)
        else:
            svg = next((v for k, v in D.items() if k in content), None)
            out.append(svg if svg else "```\n" + content + "\n```")
        i = j + 1
    else:
        out.append(lines[i]); i += 1
src = "\n".join(out)

# двойные отступы вложенных списков (2->4)
o2 = []; inf = False
for l in src.split("\n"):
    st = l.lstrip(" ")
    if st.startswith("```") or st.startswith("<div") or st.startswith("<svg"):
        o2.append(l); continue
    n = len(l) - len(st)
    o2.append(" " * (2 * n) + st if n else l)
src = "\n".join(o2)

# пустые строки вокруг списков/таблиц/блоков
def islist(s): return bool(re.match(r"(-|\*|\d+\.)\s", s.lstrip()))
res = []; prev = None
for l in src.split("\n"):
    isblk = l.lstrip().startswith(("<div", "<svg", "|"))
    if prev is not None and prev.strip() != "":
        if (islist(l) and not islist(prev)) or (l.lstrip().startswith("|") and not prev.lstrip().startswith("|")):
            res.append("")
    if l.lstrip().startswith("<div class=\"fig\"") and prev is not None and prev.strip() != "":
        res.append("")
    res.append(l); prev = l
src = "\n".join(res)
src = src.replace("\n---\n", "\n---\n\n[TOC]\n", 1)

body = markdown.markdown(src, extensions=["tables", "fenced_code", "toc", "sane_lists", "md_in_html"])
body = body.replace("<p>" + PIPE + "</p>", pipeline_html()).replace(PIPE, pipeline_html())
# markdown мог обернуть наши <div class=fig> в <p> — развернём
body = re.sub(r"<p>(<div class=\"fig\">)", r"\1", body)
body = re.sub(r"(</svg></div>)</p>", r"\1", body)
body = re.sub(r"(</div>)</p>", r"\1", body)

CSS = r"""
:root{--bg:#0c0f14;--panel:#11161d;--panel2:#161d27;--fg:#e7eef5;--muted:#9fb0c0;
--acc:#46d09a;--acc2:#4cc0f0;--line:#1f2935;--code:#0a0e13}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:
 radial-gradient(900px 500px at 80% -5%,rgba(76,192,240,.06),transparent),
 radial-gradient(700px 500px at -5% 10%,rgba(70,208,154,.05),transparent),var(--bg);
 color:var(--fg);font:400 16px/1.62 "IBM Plex Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1020px;margin:0 auto;padding:30px 24px 120px}
.masthead{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:16px}
.masthead h1{font-weight:700;font-size:1.5rem;margin:0;letter-spacing:-.01em}
.masthead .sub{color:var(--muted);font-size:.92rem}
h1{font-size:1.42rem;font-weight:700;margin:2.6em 0 .2em}
h2{font-size:1.12rem;font-weight:600;margin:2.3em 0 .55em;padding:.4em .8em;line-height:1.4;
 color:#eafff7;background:linear-gradient(90deg,rgba(70,208,154,.13),rgba(70,208,154,.02));
 border-left:3px solid var(--acc);border-radius:5px;scroll-margin-top:14px}
p{margin:.55em 0}
ul,ol{padding-left:1.4em;margin:.5em 0}li{margin:.34em 0}li>ul,li>ol{margin:.3em 0}
strong{color:#fff;font-weight:600}em{color:var(--muted);font-style:normal;font-size:.92em}
a{color:var(--acc2);text-decoration:none}a:hover{text-decoration:underline}
code{background:var(--code);color:#bfe3ff;border:1px solid var(--line);padding:.06em .4em;border-radius:5px;
 font-family:"IBM Plex Mono",Consolas,monospace;font-size:.85em}
blockquote{background:var(--panel2);border:1px solid var(--line);border-left:4px solid var(--acc);
 border-radius:9px;margin:1em 0;padding:.7em 1.1em;color:#d8e4f0}blockquote strong{color:var(--acc)}
hr{border:0;border-top:1px solid var(--line);margin:2.4em 0}
table{border-collapse:collapse;width:100%;margin:.8em 0;font-size:.92rem;background:var(--panel);
 border:1px solid var(--line);border-radius:9px;overflow:hidden}
th,td{border:1px solid var(--line);padding:7px 11px;text-align:left;vertical-align:top}
th{background:var(--panel2);color:#eafff7;font-weight:600}tr:nth-child(even) td{background:rgba(255,255,255,.012)}
.fig{background:linear-gradient(180deg,#10161e,#0c1117);border:1px solid var(--line);border-radius:12px;
 padding:16px;margin:1.1em 0;text-align:center;box-shadow:0 1px 0 rgba(255,255,255,.03) inset}
.fig svg{max-width:100%;height:auto}.cap{color:var(--muted);font-size:.84rem;margin:6px 0}
table.pipe{width:auto;margin:6px auto;border:0;background:none;font-family:"IBM Plex Mono",monospace}
table.pipe th{background:none;border:0;color:var(--muted);font-weight:500;padding:3px 8px;font-size:.8rem}
table.pipe td{border:1px solid var(--line);width:46px;height:30px;text-align:center;color:#06121a;font-weight:700;font-size:.78rem}
.pp.s1{background:#4cc0f0}.pp.s2{background:#5ed6a3}.pp.s3{background:#ffd166}.pp.s4{background:#f6a96b}.pp.s5{background:#e07a8b}
.toc{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:14px 20px;margin:1.3em 0;font-size:.85rem;columns:2;column-gap:34px}
.toc>ul{margin:0;padding:0}.toc ul{list-style:none;padding-left:.7em;margin:.12em 0}
.toc>ul>li{break-inside:avoid;margin:.12em 0}.toc a{color:#c3d2e0}.toc a:hover{color:var(--acc2)}
.toc>ul>li>a{color:var(--acc);font-weight:600}
@media(max-width:640px){.toc{columns:1}.wrap{padding:18px 14px}body{font-size:15px}}
@media print{body{background:#fff;color:#000}.wrap{max-width:100%}.fig,table{page-break-inside:avoid}}
"""
HEAD = ('<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Конспект АСВТ — экзамен</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">'
        '<style>' + CSS + '</style></head><body><div class="wrap">'
        '<div class="masthead"><h1>Конспект АСВТ</h1><span class="sub">экзамен · Семенов П.О. · 55 билетов</span></div>')
open(OUT, "w", encoding="utf-8").write(HEAD + body + "</div></body></html>")
print("OK ->", OUT, "| svg-схем:", body.count("<svg"), "| конвейер:", body.count('table class="pipe"'),
      "| таблиц данных:", len(re.findall(r"<table>", body)), "| ul:", body.count("<ul"))
