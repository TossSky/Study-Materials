#!/usr/bin/env python3
"""Python-эмулятор TCP-сервера для проверки tcpclient/tcpclient2.
Аналог tcpserveremul.rb из методички. Слушает TCP-порт, принимает 3 байта команды
(put/get). В put-режиме читает сообщения протокола, пишет в msg.txt,
отвечает 'ok'. В get-режиме отдаёт всё из msg.txt в формате протокола.
При сообщении 'stop' завершается.

Запуск: python3 tcp_server_emul.py [PORT]
"""

import socket
import struct
import sys
import threading

PHONE_LEN = 12
HEAD_SZ   = 4 + PHONE_LEN * 2 + 3
LOG_LOCK  = threading.Lock()


def log_msg(peer, phone1, phone2, h, m, s, text):
    with LOG_LOCK:
        with open('msg.txt', 'a') as f:
            f.write(f'{peer} {phone1.decode()} {phone2.decode()} '
                    f'{h:02d}:{m:02d}:{s:02d} {text.decode("utf-8", "replace")}\n')


def parse_one(buf):
    """Парсит одно сообщение из буфера. Возвращает (consumed, fields) или (0, None)."""
    if len(buf) < HEAD_SZ:
        return 0, None
    term = buf.find(b'\x00', HEAD_SZ)
    if term < 0:
        return 0, None
    idx, = struct.unpack('!I', buf[:4])
    phone1 = buf[4:4 + PHONE_LEN]
    phone2 = buf[4 + PHONE_LEN:4 + PHONE_LEN * 2]
    h = buf[4 + PHONE_LEN * 2]
    m = buf[4 + PHONE_LEN * 2 + 1]
    s = buf[4 + PHONE_LEN * 2 + 2]
    text = buf[HEAD_SZ:term]
    return term + 1, (idx, phone1, phone2, h, m, s, text)


def send_stored(conn):
    """Режим get: читает msg.txt и пакует каждую строку в формат протокола."""
    try:
        with open('msg.txt', 'r') as f:
            lines = [ln.rstrip('\n').rstrip('\r') for ln in f if ln.strip()]
    except FileNotFoundError:
        return
    for idx, line in enumerate(lines):
        try:
            peer, phone1, phone2, tm, *rest = line.split(' ', 4)
            text = rest[0] if rest else ''
            h, m, s = (int(x) for x in tm.split(':'))
            pkt = (struct.pack('!I', idx) +
                   phone1.encode().ljust(PHONE_LEN, b' ')[:PHONE_LEN] +
                   phone2.encode().ljust(PHONE_LEN, b' ')[:PHONE_LEN] +
                   bytes([h, m, s]) + text.encode() + b'\x00')
            conn.sendall(pkt)
        except Exception as e:
            print(f'send_stored: skip line: {e}', file=sys.stderr)


STOP_REQUEST = threading.Event()


def handle_client(conn, addr):
    peer = f'{addr[0]}:{addr[1]}'
    print(f'connected: {peer}')
    buf = b''
    mode = None
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            if mode is None:
                if len(buf) < 3:
                    continue
                mode = buf[:3]
                buf = buf[3:]
                if mode not in (b'put', b'get'):
                    print(f'bad mode from {peer}: {mode!r}')
                    return
            if mode == b'put':
                while True:
                    consumed, fields = parse_one(buf)
                    if consumed == 0:
                        break
                    buf = buf[consumed:]
                    idx, phone1, phone2, h, m, s, text = fields
                    log_msg(peer, phone1, phone2, h, m, s, text)
                    conn.sendall(b'ok')
                    if text == b'stop':
                        print('"stop" received, server will terminate')
                        STOP_REQUEST.set()
                        return
            elif mode == b'get':
                send_stored(conn)
                return
    finally:
        conn.close()
        print(f'disconnected: {peer}')


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(16)
    s.settimeout(0.5)
    print(f'listening TCP: {port}')
    while not STOP_REQUEST.is_set():
        try:
            conn, addr = s.accept()
        except socket.timeout:
            continue
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()
    s.close()
    print('server stopped')


if __name__ == '__main__':
    main()
