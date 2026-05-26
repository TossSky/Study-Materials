# -*- coding: utf-8 -*-
"""Генерация sequence-диаграмм TCP и UDP взаимодействия.
Создаёт PNG-файлы tcp_seq.png и udp_seq.png для встраивания в отчёт.
"""

from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(os.path.abspath(__file__))

FONT_PATH      = 'C:/Windows/Fonts/times.ttf'
FONT_BOLD_PATH = 'C:/Windows/Fonts/timesbd.ttf'

W = 1400
LIFE_X_CLIENT = 280
LIFE_X_SERVER = 1120
ROW_H         = 50
MARGIN_TOP    = 100
MARGIN_BOT    = 60
BOX_W         = 220
BOX_H         = 50

font_title = ImageFont.truetype(FONT_BOLD_PATH, 22)
font_box   = ImageFont.truetype(FONT_BOLD_PATH, 20)
font_arr   = ImageFont.truetype(FONT_PATH, 16)
font_note  = ImageFont.truetype(FONT_PATH, 15)


def draw_seq(out_path, title, events):
    """events: list of (kind, text) where kind:
        'c2s'   : клиент -> сервер
        's2c'   : сервер -> клиент
        'lost'  : клиент -> сервер, пакет потерян (зачёркнут красным)
        'note'  : текстовая заметка между линиями жизни (без стрелки)
    """
    h = MARGIN_TOP + ROW_H * len(events) + MARGIN_BOT
    img = Image.new('RGB', (W, h), 'white')
    d = ImageDraw.Draw(img)

    # Заголовок
    tw = d.textlength(title, font=font_title)
    d.text(((W - tw) / 2, 20), title, fill='black', font=font_title)

    # Прямоугольники "Клиент" / "Сервер"
    for x, label in [(LIFE_X_CLIENT, 'Клиент'), (LIFE_X_SERVER, 'Сервер')]:
        d.rectangle([x - BOX_W // 2, 55, x + BOX_W // 2, 55 + BOX_H],
                    outline='black', width=2, fill='#e8e8e8')
        lw = d.textlength(label, font=font_box)
        d.text((x - lw / 2, 65), label, fill='black', font=font_box)

    # Линии жизни (пунктир: серия коротких отрезков)
    bottom_y = MARGIN_TOP + ROW_H * len(events) + 20
    for x in (LIFE_X_CLIENT, LIFE_X_SERVER):
        y = 55 + BOX_H
        while y < bottom_y:
            d.line([(x, y), (x, y + 6)], fill='black', width=2)
            y += 12

    # Сообщения
    for i, (kind, text) in enumerate(events):
        y = MARGIN_TOP + i * ROW_H

        if kind == 'note':
            tw = d.textlength(text, font=font_note)
            cx = (LIFE_X_CLIENT + LIFE_X_SERVER) / 2
            d.rectangle([cx - tw / 2 - 8, y - 4, cx + tw / 2 + 8, y + 22],
                        outline='#888888', fill='#fff8d6', width=1)
            d.text((cx - tw / 2, y), text, fill='#444444', font=font_note)
            continue

        if kind == 'c2s' or kind == 'lost':
            x0, x1 = LIFE_X_CLIENT, LIFE_X_SERVER
            color  = 'red' if kind == 'lost' else 'black'
        else:  # s2c
            x0, x1 = LIFE_X_SERVER, LIFE_X_CLIENT
            color  = 'black'

        # Линия стрелки
        d.line([(x0, y + 18), (x1, y + 18)], fill=color, width=2)
        # Наконечник стрелки
        if x1 > x0:
            d.polygon([(x1, y + 18), (x1 - 12, y + 12), (x1 - 12, y + 24)], fill=color)
        else:
            d.polygon([(x1, y + 18), (x1 + 12, y + 12), (x1 + 12, y + 24)], fill=color)

        # Подпись над стрелкой
        tw = d.textlength(text, font=font_arr)
        cx = (x0 + x1) / 2
        d.text((cx - tw / 2, y - 4), text, fill=color, font=font_arr)

        # Для потерянного пакета — красное "X" в районе сервера
        if kind == 'lost':
            cx_lost = x1 - 60
            d.line([(cx_lost - 10, y + 8), (cx_lost + 10, y + 28)],  fill='red', width=3)
            d.line([(cx_lost + 10, y + 8), (cx_lost - 10, y + 28)],  fill='red', width=3)

    img.save(out_path)


# ----- TCP put-сценарий -----
tcp_events = [
    ('c2s',  'connect'),
    ('note', 'accept()'),
    ('c2s',  '"put" (3 байта)'),
    ('c2s',  'msg #0 (idx + phone1 + phone2 + h + m + s + msg + \\0)'),
    ('c2s',  'msg #1'),
    ('c2s',  'msg #2'),
    ('s2c',  '"ok"'),
    ('s2c',  '"ok"'),
    ('s2c',  '"ok"'),
    ('c2s',  'close'),
]
draw_seq(os.path.join(BASE, 'tcp_seq.png'),
         'Временная диаграмма TCP put-сценария',
         tcp_events)


# ----- UDP с потерей пакета -----
udp_events = [
    ('c2s',  'dgram msg #0'),
    ('c2s',  'dgram msg #1'),
    ('c2s',  'dgram msg #2'),
    ('s2c',  'ack [2, 1, 0]'),
    ('s2c',  'ack [2, 1, 0]'),
    ('s2c',  'ack [2, 1, 0]'),
    ('note', 'select(100 мс): новых ack нет, отправляем дальше'),
    ('c2s',  'dgram msg #3'),
    ('lost', 'dgram msg #4 (потеря пакета)'),
    ('s2c',  'ack [3, 2, 1, 0]'),
    ('note', 'select истёк: msg #4 не подтверждён, повтор'),
    ('c2s',  'dgram msg #4 (retry)'),
    ('s2c',  'ack [4, 3, 2, 1, 0]'),
]
draw_seq(os.path.join(BASE, 'udp_seq.png'),
         'Временная диаграмма UDP с потерей пакета',
         udp_events)

print('diagrams generated')
