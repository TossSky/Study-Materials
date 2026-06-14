# -*- coding: utf-8 -*-
"""Рендеринг диаграмм для ЛР3 ОС.

Использует PlantUML (worker_flow.puml + time_diagram.puml).
PlantUML.jar лежит рядом со скриптом.

Запуск: python generate_diagrams.py
Выход:  worker_flow.png, time_diagram.png
"""

import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.join(BASE, 'plantuml.jar')
SOURCES = ['worker_flow.puml', 'time_diagram.puml']


def main():
    if not os.path.isfile(JAR):
        print(f'plantuml.jar не найден по пути {JAR}', file=sys.stderr)
        print('Скачайте: https://github.com/plantuml/plantuml/releases',
              file=sys.stderr)
        sys.exit(1)

    cmd = ['java', '-jar', JAR, '-tpng', '-charset', 'UTF-8'] + SOURCES
    print('Команда:', ' '.join(cmd))
    res = subprocess.run(cmd, cwd=BASE)
    if res.returncode != 0:
        print(f'PlantUML вернул код {res.returncode}', file=sys.stderr)
        sys.exit(res.returncode)

    for src in SOURCES:
        png = os.path.join(BASE, src.replace('.puml', '.png'))
        if os.path.isfile(png):
            print(f'OK: {png}')
        else:
            print(f'НЕТ: {png}', file=sys.stderr)


if __name__ == '__main__':
    main()
