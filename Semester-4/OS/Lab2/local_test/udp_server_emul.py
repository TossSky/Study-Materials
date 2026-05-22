#!/usr/bin/env python3
"""Python-эмулятор UDP-сервера. Принимает дейтаграммы от клиентов, ведёт базу
по IP+порту, пишет уникальные сообщения в msg.txt, отвечает дейтаграммой
со списком последних принятых индексов.

Запуск: python3 udp_server_emul.py PORT
"""

import socket
import struct
import sys

PHONE_LEN = 12
HEAD_SZ   = 4 + PHONE_LEN * 2 + 3
MAX_PER   = 20

db = {}   # peer -> list[idx]


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8700
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    print(f'listening UDP: {port}')
    while True:
        dg, peer = s.recvfrom(65535)
        if len(dg) < HEAD_SZ + 1:
            continue
        idx, = struct.unpack('!I', dg[:4])
        ip_port = f'{peer[0]}:{peer[1]}'
        if ip_port not in db:
            db[ip_port] = []
        recs = db[ip_port]
        if idx not in recs:
            term = dg.find(b'\x00', HEAD_SZ)
            if term < 0:
                continue
            phone1 = dg[4:4 + PHONE_LEN].decode()
            phone2 = dg[4 + PHONE_LEN:4 + PHONE_LEN * 2].decode()
            h, m, sec = dg[4 + PHONE_LEN * 2], dg[4 + PHONE_LEN * 2 + 1], dg[4 + PHONE_LEN * 2 + 2]
            text = dg[HEAD_SZ:term].decode('utf-8', 'replace')
            with open('msg.txt', 'a') as f:
                f.write(f'{ip_port} {phone1} {phone2} {h:02d}:{m:02d}:{sec:02d} {text}\n')
            recs.append(idx)
            if len(recs) > MAX_PER:
                recs.pop(0)
            if text == 'stop':
                ack = b''.join(struct.pack('!I', r) for r in reversed(recs[-MAX_PER:]))
                s.sendto(ack, peer)
                print('"stop" received, terminating')
                break
        ack = b''.join(struct.pack('!I', r) for r in reversed(recs[-MAX_PER:]))
        s.sendto(ack, peer)
    s.close()


if __name__ == '__main__':
    main()
