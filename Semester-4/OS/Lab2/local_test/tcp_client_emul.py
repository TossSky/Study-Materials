#!/usr/bin/env python3
"""Python-эмулятор TCP-клиента. Читает входной файл и отправляет сообщения
на сервер, потом принимает 'ok' на каждое.

Запуск: python3 tcp_client_emul.py HOST:PORT FILE
"""

import socket
import struct
import sys
import time

PHONE_LEN = 12


def build_msg(idx, line):
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

    s = None
    for _ in range(10):
        try:
            s = socket.create_connection((host, port), timeout=5)
            break
        except OSError:
            time.sleep(0.1)
    if s is None:
        print('connect failed')
        sys.exit(1)

    s.sendall(b'put')

    cnt = 0
    with open(sys.argv[2]) as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        msg = build_msg(i, line)
        if msg is None:
            print(f'skip line {i}')
            continue
        s.sendall(msg)
        cnt += 1

    for _ in range(cnt):
        buf = b''
        while len(buf) < 2:
            r = s.recv(2 - len(buf))
            if not r:
                print(f'connection lost, got {len(buf)} of 2')
                sys.exit(1)
            buf += r
        if buf != b'ok':
            print(f'bad ack: {buf!r}')
            sys.exit(1)

    s.close()
    print(f'done: {cnt} messages sent and acked')


if __name__ == '__main__':
    main()
