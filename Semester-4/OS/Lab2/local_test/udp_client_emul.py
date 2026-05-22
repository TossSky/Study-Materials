#!/usr/bin/env python3
"""Python-эмулятор UDP-клиента для проверки udpserver.
Шлёт дейтаграммы из входного файла, принимает ack-дейтаграммы и повторяет
отправку неподтверждённых до достижения цели (20 или все).

Запуск: python3 udp_client_emul.py HOST:PORT FILE
"""

import socket
import struct
import sys
import time
import select

PHONE_LEN = 12
HEAD_SZ   = 4 + PHONE_LEN * 2 + 3


def build_dgram(idx, line):
    parts = line.strip().split(' ', 3)
    if len(parts) != 4:
        return None
    phone1, phone2, tm, msg = parts
    if len(phone1) != PHONE_LEN or len(phone2) != PHONE_LEN:
        return None
    try:
        h, m, s = (int(x) for x in tm.split(':'))
    except ValueError:
        return None
    return (struct.pack('!I', idx) +
            phone1.encode() + phone2.encode() +
            bytes([h, m, s]) + msg.encode() + b'\x00')


def main():
    ep = sys.argv[1].split(':')
    host, port = ep[0], int(ep[1])
    with open(sys.argv[2]) as f:
        lines = f.read().splitlines()

    msgs = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        dg = build_dgram(i, line)
        if dg:
            msgs.append((i, dg, False))   # (idx, datagram, acked)

    target = min(20, len(msgs))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (host, port)
    round_n = 0
    while sum(1 for _, _, a in msgs if a) < target:
        round_n += 1
        sent = 0
        for i in range(len(msgs)):
            idx, dg, acked = msgs[i]
            if acked:
                continue
            sock.sendto(dg, addr)
            sent += 1
        # ждём ack до 100 мс, читаем все доступные дейтаграммы
        deadline = time.time() + 0.1
        while True:
            timeout = deadline - time.time()
            if timeout <= 0:
                break
            rd, _, _ = select.select([sock], [], [], timeout)
            if not rd:
                break
            while True:
                rd2, _, _ = select.select([sock], [], [], 0)
                if not rd2:
                    break
                data, _ = sock.recvfrom(65535)
                for j in range(0, len(data), 4):
                    if j + 4 > len(data):
                        break
                    idx, = struct.unpack('!I', data[j:j+4])
                    for k in range(len(msgs)):
                        if msgs[k][0] == idx and not msgs[k][2]:
                            msgs[k] = (msgs[k][0], msgs[k][1], True)
                            break
            break
        acked_now = sum(1 for _, _, a in msgs if a)
        print(f'round {round_n}: sent {sent}, acked {acked_now}/{target}')
        if round_n > 1000:
            print('giving up')
            break
    sock.close()
    print(f'done: acked {sum(1 for _, _, a in msgs if a)}/{len(msgs)}')


if __name__ == '__main__':
    main()
