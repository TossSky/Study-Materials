#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define MAX_CLIENTS    64
#define BUF_CAPACITY   8192
#define PHONE_LEN      12
#define HEAD_SZ        (4 + PHONE_LEN + PHONE_LEN + 3)  // 31 байт фикс. шапки сообщения

enum ClientMode { MODE_UNKNOWN = 0, MODE_PUT = 1, MODE_GET = 2 };

// Состояние одного клиента: сокет, режим, накопительный буфер, адрес.
struct Client {
    SOCKET     sock;
    int        mode;
    char       buf[BUF_CAPACITY];
    int        buf_len;
    char       peer[32];      // "ip:port" для лога
    SOCKADDR_IN addr;
};

static Client    g_clients[MAX_CLIENTS];
static int       g_client_cnt = 0;
static SOCKET    g_listen     = INVALID_SOCKET;
static WSAEVENT  g_ev_listen  = WSA_INVALID_EVENT;
static WSAEVENT  g_ev_client  = WSA_INVALID_EVENT;
static int       g_stop_flag  = 0;

// Форматирование строки "ip:port" в peer-поле клиента.
static void format_peer(Client* c)
{
    unsigned long ip = ntohl(c->addr.sin_addr.s_addr);
    sprintf(c->peer, "%lu.%lu.%lu.%lu:%hu",
            (ip >> 24) & 0xFF, (ip >> 16) & 0xFF,
            (ip >> 8) & 0xFF,  ip & 0xFF,
            ntohs(c->addr.sin_port));
}

// Закрытие клиента и удаление из массива.
static void drop_client(int idx)
{
    if (idx < 0 || idx >= g_client_cnt) return;
    closesocket(g_clients[idx].sock);
    g_clients[idx] = g_clients[g_client_cnt - 1];
    --g_client_cnt;
}

// Закрытие всех клиентов (вызывается перед завершением сервера).
static void close_all_clients()
{
    for (int i = 0; i < g_client_cnt; ++i) closesocket(g_clients[i].sock);
    g_client_cnt = 0;
}

// Дозапись в msg.txt одного сообщения в текстовом формате.
static void log_message(const char* peer, const char* phone1, const char* phone2,
                        unsigned char h, unsigned char m, unsigned char s,
                        const char* text)
{
    FILE* f = fopen("msg.txt", "a");
    if (!f) return;
    fprintf(f, "%s %.*s %.*s %02u:%02u:%02u %s\n",
            peer, PHONE_LEN, phone1, PHONE_LEN, phone2,
            (unsigned)h, (unsigned)m, (unsigned)s, text);
    fclose(f);
}

// Попытка извлечь одно сообщение из накопительного буфера клиента.
// Возвращает: 1 - извлечено, 0 - данных пока недостаточно, -1 - ошибка протокола.
// При успехе записывает в out_text текст сообщения и сообщает, был ли это "stop".
static int try_parse_message(Client* c, int* out_is_stop)
{
    *out_is_stop = 0;
    if (c->buf_len < HEAD_SZ) return 0;

    // Ищем нулевой байт начиная с позиции HEAD_SZ.
    int term = -1;
    for (int i = HEAD_SZ; i < c->buf_len; ++i) {
        if (c->buf[i] == 0) { term = i; break; }
    }
    if (term < 0) {
        if (c->buf_len >= BUF_CAPACITY) return -1;  // переполнение
        return 0;
    }

    const char*   phone1 = c->buf + 4;
    const char*   phone2 = c->buf + 4 + PHONE_LEN;
    unsigned char h      = (unsigned char)c->buf[4 + PHONE_LEN + PHONE_LEN];
    unsigned char m      = (unsigned char)c->buf[4 + PHONE_LEN + PHONE_LEN + 1];
    unsigned char s      = (unsigned char)c->buf[4 + PHONE_LEN + PHONE_LEN + 2];
    const char*   text   = c->buf + HEAD_SZ;
    int           tlen   = term - HEAD_SZ;

    log_message(c->peer, phone1, phone2, h, m, s, text);
    if (tlen == 4 && memcmp(text, "stop", 4) == 0) *out_is_stop = 1;

    // Сдвинуть буфер на размер обработанного сообщения.
    int consumed = term + 1;
    int rest     = c->buf_len - consumed;
    if (rest > 0) memmove(c->buf, c->buf + consumed, rest);
    c->buf_len = rest;
    return 1;
}

// Отправка ровно len байт в сокет, учёт частичной записи.
static int send_all(SOCKET s, const char* buf, int len)
{
    int sent = 0;
    while (sent < len) {
        int n = send(s, buf + sent, len - sent, 0);
        if (n <= 0) {
            if (WSAGetLastError() == WSAEWOULDBLOCK) { Sleep(1); continue; }
            return -1;
        }
        sent += n;
    }
    return 0;
}

// Обработка получения для одного клиента: чтение, парсинг, ответы.
// Возвращает 0 - продолжать работу, -1 - закрыть клиента, 1 - получен stop.
static int handle_recv(Client* c)
{
    int n = recv(c->sock, c->buf + c->buf_len, BUF_CAPACITY - c->buf_len, 0);
    if (n == 0) return -1;
    if (n < 0) {
        int err = WSAGetLastError();
        if (err == WSAEWOULDBLOCK) return 0;
        return -1;
    }
    c->buf_len += n;

    // Если режим ещё не определён, ждём 3 байта команды.
    if (c->mode == MODE_UNKNOWN) {
        if (c->buf_len < 3) return 0;
        if      (memcmp(c->buf, "put", 3) == 0) c->mode = MODE_PUT;
        else if (memcmp(c->buf, "get", 3) == 0) c->mode = MODE_GET;
        else { fprintf(stderr, "bad mode from %s\n", c->peer); return -1; }
        int rest = c->buf_len - 3;
        if (rest > 0) memmove(c->buf, c->buf + 3, rest);
        c->buf_len = rest;
    }

    if (c->mode == MODE_PUT) {
        for (;;) {
            int is_stop = 0;
            int r = try_parse_message(c, &is_stop);
            if (r < 0) { fprintf(stderr, "proto err from %s\n", c->peer); return -1; }
            if (r == 0) break;
            if (send_all(c->sock, "ok", 2) != 0) return -1;
            if (is_stop) return 1;
        }
    } else if (c->mode == MODE_GET) {
        // Команду get обработаем после установки режима в send-обработчике.
        return 2;
    }
    return 0;
}

// Чтение из msg.txt одной строки и отправка её клиенту как сообщения протокола.
// idx - индекс сообщения, который кладётся в первые 4 байта пакета.
static int send_one_stored(SOCKET s, const char* line, unsigned int idx)
{
    // Строка: "ip:port phone1 phone2 hh:mm:ss Message"
    const char* sp = strchr(line, ' ');
    if (!sp) return 0;
    const char* phone1 = sp + 1;
    const char* sp2    = strchr(phone1, ' ');
    if (!sp2 || sp2 - phone1 != PHONE_LEN) return 0;
    const char* phone2 = sp2 + 1;
    const char* sp3    = strchr(phone2, ' ');
    if (!sp3 || sp3 - phone2 != PHONE_LEN) return 0;
    const char* tm     = sp3 + 1;
    if (strlen(tm) < 8 || tm[2] != ':' || tm[5] != ':') return 0;
    int h = (tm[0]-'0')*10 + (tm[1]-'0');
    int m = (tm[3]-'0')*10 + (tm[4]-'0');
    int ss = (tm[6]-'0')*10 + (tm[7]-'0');
    const char* msg = tm + 9;  // "hh:mm:ss " - 9 символов
    int msg_len = (int)strlen(msg);

    int total = HEAD_SZ + msg_len + 1;
    char* out = (char*)malloc(total);
    if (!out) return 0;
    unsigned int idx_be = htonl(idx);
    int off = 0;
    memcpy(out + off, &idx_be, 4); off += 4;
    memcpy(out + off, phone1, PHONE_LEN); off += PHONE_LEN;
    memcpy(out + off, phone2, PHONE_LEN); off += PHONE_LEN;
    out[off++] = (char)h;
    out[off++] = (char)m;
    out[off++] = (char)ss;
    memcpy(out + off, msg, msg_len); off += msg_len;
    out[off++] = 0;
    int rc = send_all(s, out, total);
    free(out);
    return rc;
}

// Обработка режима get: прочитать msg.txt и отправить все сообщения клиенту.
static void handle_get(Client* c)
{
    FILE* f = fopen("msg.txt", "r");
    if (f) {
        char line[BUF_CAPACITY];
        unsigned int idx = 0;
        while (fgets(line, sizeof(line), f)) {
            size_t n = strlen(line);
            while (n > 0 && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
            if (n == 0) continue;
            if (send_one_stored(c->sock, line, idx) != 0) break;
            ++idx;
        }
        fclose(f);
    }
}

// Регистрация всех активных клиентов в общем событии g_ev_client.
static void rebind_client_events()
{
    for (int i = 0; i < g_client_cnt; ++i) {
        WSAEventSelect(g_clients[i].sock, g_ev_client, FD_READ | FD_CLOSE);
    }
}

// Принятие нового подключения с прослушивающего сокета.
static void on_accept()
{
    SOCKADDR_IN a;
    int alen = sizeof(a);
    SOCKET s = accept(g_listen, (SOCKADDR*)&a, &alen);
    if (s == INVALID_SOCKET) return;
    if (g_client_cnt >= MAX_CLIENTS) {
        fprintf(stderr, "no free slot, dropping client\n");
        closesocket(s);
        return;
    }
    u_long mode = 1; ioctlsocket(s, FIONBIO, &mode);
    Client* c = &g_clients[g_client_cnt++];
    memset(c, 0, sizeof(*c));
    c->sock = s;
    c->mode = MODE_UNKNOWN;
    c->addr = a;
    format_peer(c);
    WSAEventSelect(s, g_ev_client, FD_READ | FD_CLOSE);
    printf("connected: %s\n", c->peer);
}

// Главный цикл сервера: ожидание событий и диспетчеризация.
static int run_server(int port)
{
    g_listen = socket(AF_INET, SOCK_STREAM, 0);
    if (g_listen == INVALID_SOCKET) {
        fprintf(stderr, "socket failed: %d\n", WSAGetLastError());
        return 1;
    }
    int yes = 1;
    setsockopt(g_listen, SOL_SOCKET, SO_REUSEADDR, (const char*)&yes, sizeof(yes));

    SOCKADDR_IN addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port        = htons((unsigned short)port);
    if (bind(g_listen, (SOCKADDR*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        fprintf(stderr, "bind failed: %d\n", WSAGetLastError());
        return 1;
    }
    if (listen(g_listen, SOMAXCONN) == SOCKET_ERROR) {
        fprintf(stderr, "listen failed: %d\n", WSAGetLastError());
        return 1;
    }

    u_long nb = 1; ioctlsocket(g_listen, FIONBIO, &nb);
    g_ev_listen = WSACreateEvent();
    g_ev_client = WSACreateEvent();
    WSAEventSelect(g_listen, g_ev_listen, FD_ACCEPT);

    printf("listening: %d\n", port);

    while (!g_stop_flag) {
        WSAEVENT evs[2] = { g_ev_listen, g_ev_client };
        DWORD r = WSAWaitForMultipleEvents(2, evs, FALSE, 1000, FALSE);
        if (r == WSA_WAIT_TIMEOUT) continue;
        if (r == WSA_WAIT_FAILED) break;

        WSAResetEvent(g_ev_listen);
        WSAResetEvent(g_ev_client);

        WSANETWORKEVENTS ne;
        if (WSAEnumNetworkEvents(g_listen, g_ev_listen, &ne) == 0 &&
            (ne.lNetworkEvents & FD_ACCEPT)) {
            on_accept();
        }

        for (int i = 0; i < g_client_cnt; ) {
            Client* c = &g_clients[i];
            int has_event = (WSAEnumNetworkEvents(c->sock, g_ev_client, &ne) == 0);
            int rm = 0;
            if (has_event && (ne.lNetworkEvents & FD_READ)) {
                int rc = handle_recv(c);
                if (rc == 1) { g_stop_flag = 1; }   // "stop"
                else if (rc == 2) { handle_get(c); rm = 1; }
                else if (rc < 0)  rm = 1;
            }
            if (has_event && (ne.lNetworkEvents & FD_CLOSE) && !rm) rm = 1;
            if (rm) {
                printf("disconnected: %s\n", c->peer);
                drop_client(i);
            } else ++i;
        }

        if (g_stop_flag) break;
        rebind_client_events();
    }

    close_all_clients();
    closesocket(g_listen);
    if (g_ev_listen != WSA_INVALID_EVENT) WSACloseEvent(g_ev_listen);
    if (g_ev_client != WSA_INVALID_EVENT) WSACloseEvent(g_ev_client);
    return 0;
}

int main(int argc, char** argv)
{
    if (argc != 2) { fprintf(stderr, "Usage: %s PORT\n", argv[0]); return 1; }
    int port = atoi(argv[1]);
    if (port <= 0 || port > 65535) { fprintf(stderr, "bad port\n"); return 1; }

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "WSAStartup failed\n"); return 1;
    }
    int rc = run_server(port);
    WSACleanup();
    return rc;
}
