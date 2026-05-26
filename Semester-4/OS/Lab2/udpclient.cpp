#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define PHONE_LEN  12
#define HEAD_SZ    (4 + PHONE_LEN + PHONE_LEN + 3)
#define MAX_MSGS   4096
#define MAX_DGRAM  65507
#define TARGET_ACK 20            // нужно подтвердить минимум 20 сообщений (или все)
#define WAIT_MS    100           // таймаут ожидания ответа от сервера

// Одно сообщение из исходного файла: сформированная дейтаграмма + флаг подтверждения.
struct Msg {
    char buf[2048];
    int  len;
    int  acked;
};

static Msg g_msgs[MAX_MSGS];
static int g_msg_cnt = 0;

// Парсинг "IP:PORT".
static int parse_endpoint(const char* arg, char* ip, int ip_sz, int* port)
{
    const char* colon = strchr(arg, ':');
    if (!colon) return -1;
    int n = (int)(colon - arg);
    if (n <= 0 || n >= ip_sz) return -1;
    memcpy(ip, arg, n); ip[n] = 0;
    *port = atoi(colon + 1);
    return (*port > 0 && *port <= 65535) ? 0 : -1;
}

// Валидация номера телефона: 12 символов, "+7" и 10 цифр.
static int is_phone(const char* s)
{
    if (s[0] != '+' || s[1] != '7') return 0;
    for (int i = 2; i < PHONE_LEN; ++i)
        if (s[i] < '0' || s[i] > '9') return 0;
    return 1;
}

// Парсинг "hh:mm:ss" с проверкой диапазонов.
static int parse_time(const char* s, unsigned char* h, unsigned char* m, unsigned char* sec)
{
    if (strlen(s) < 8) return -1;
    if (s[2] != ':' || s[5] != ':') return -1;
    for (int i = 0; i < 8; ++i)
        if (i != 2 && i != 5 && (s[i] < '0' || s[i] > '9')) return -1;
    int hh = (s[0]-'0')*10 + (s[1]-'0');
    int mm = (s[3]-'0')*10 + (s[4]-'0');
    int ss = (s[6]-'0')*10 + (s[7]-'0');
    if (hh > 23 || mm > 59 || ss > 59) return -1;
    *h = (unsigned char)hh; *m = (unsigned char)mm; *sec = (unsigned char)ss;
    return 0;
}

// Сборка бинарной дейтаграммы из одной строки исходного файла.
static int build_datagram(const char* line, unsigned int idx, char* out, int out_sz)
{
    const char* p = line;
    while (*p == ' ' || *p == '\t') ++p;
    if (!*p) return -1;

    char phone1[PHONE_LEN + 1], phone2[PHONE_LEN + 1], tm[16];
    if (sscanf(p, "%12s %12s %15s", phone1, phone2, tm) != 3) return -1;
    if (!is_phone(phone1) || !is_phone(phone2)) return -1;

    unsigned char h, m, s;
    if (parse_time(tm, &h, &m, &s) != 0) return -1;

    const char* msg = p;
    int spaces = 0;
    while (*msg && spaces < 3) { if (*msg == ' ') ++spaces; ++msg; }
    if (spaces < 3) return -1;
    int msg_len = (int)strlen(msg);

    int total = HEAD_SZ + msg_len + 1;
    if (total > out_sz) return -1;

    unsigned int idx_be = htonl(idx);
    int off = 0;
    memcpy(out + off, &idx_be, 4); off += 4;
    memcpy(out + off, phone1, PHONE_LEN); off += PHONE_LEN;
    memcpy(out + off, phone2, PHONE_LEN); off += PHONE_LEN;
    out[off++] = (char)h; out[off++] = (char)m; out[off++] = (char)s;
    memcpy(out + off, msg, msg_len); off += msg_len;
    out[off++] = 0;
    return off;
}

// Чтение файла и подготовка всех валидных сообщений в g_msgs.
static int load_messages(const char* path)
{
    FILE* f = fopen(path, "r");
    if (!f) { fprintf(stderr, "error: cannot open %s\n", path); return -1; }
    char line[2048];
    int  idx = 0;
    while (fgets(line, sizeof(line), f) && g_msg_cnt < MAX_MSGS) {
        size_t n = strlen(line);
        while (n > 0 && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
        if (n == 0) { ++idx; continue; }
        Msg* m = &g_msgs[g_msg_cnt];
        int len = build_datagram(line, (unsigned int)idx, m->buf, sizeof(m->buf));
        ++idx;
        if (len < 0) { fprintf(stderr, "skip: invalid line\n"); continue; }
        m->len   = len;
        m->acked = 0;
        ++g_msg_cnt;
    }
    fclose(f);
    return 0;
}

// Подсчёт уже подтверждённых сообщений.
static int count_acked()
{
    int c = 0;
    for (int i = 0; i < g_msg_cnt; ++i) if (g_msgs[i].acked) ++c;
    return c;
}

// Извлечение индекса сообщения из его дейтаграммы (первые 4 байта BE).
static unsigned int msg_index(const Msg* m)
{
    unsigned int v;
    memcpy(&v, m->buf, 4);
    return ntohl(v);
}

// Обработка ответа сервера: пометка подтверждённых сообщений.
static void process_ack_datagram(const char* buf, int len)
{
    int n_ids = len / 4;
    for (int i = 0; i < n_ids; ++i) {
        unsigned int v;
        memcpy(&v, buf + i * 4, 4);
        unsigned int idx = ntohl(v);
        for (int j = 0; j < g_msg_cnt; ++j) {
            if (!g_msgs[j].acked && msg_index(&g_msgs[j]) == idx) {
                g_msgs[j].acked = 1;
                break;
            }
        }
    }
}

// Отправка всех неподтверждённых сообщений на сервер.
static int send_unacked(SOCKET s, const SOCKADDR_IN* dst)
{
    int sent = 0;
    for (int i = 0; i < g_msg_cnt; ++i) {
        if (g_msgs[i].acked) continue;
        int r = sendto(s, g_msgs[i].buf, g_msgs[i].len, 0,
                       (const SOCKADDR*)dst, sizeof(*dst));
        if (r < 0) {
            fprintf(stderr, "sendto err: %d\n", WSAGetLastError());
            return -1;
        }
        ++sent;
    }
    return sent;
}

// Ожидание дейтаграмм от сервера до 100 мс. Обрабатывает все доступные.
static void wait_and_collect_acks(SOCKET s)
{
    char buf[MAX_DGRAM];
    DWORD start = GetTickCount();
    for (;;) {
        DWORD elapsed = GetTickCount() - start;
        if (elapsed >= (DWORD)WAIT_MS) break;
        fd_set rfd;
        struct timeval tv;
        tv.tv_sec  = 0;
        tv.tv_usec = (WAIT_MS - elapsed) * 1000;
        FD_ZERO(&rfd); FD_SET(s, &rfd);
        int r = select(0, &rfd, 0, 0, &tv);
        if (r <= 0) break;
        int n = recvfrom(s, buf, sizeof(buf), 0, 0, 0);
        if (n <= 0) break;
        process_ack_datagram(buf, n);
    }
}

int main(int argc, char** argv)
{
    if (argc != 3) {
        fprintf(stderr, "Usage: %s IP:PORT FILE\n", argv[0]);
        return 1;
    }
    char ip[64];
    int  port = 0;
    if (parse_endpoint(argv[1], ip, sizeof(ip), &port) != 0) {
        fprintf(stderr, "error: invalid endpoint: %s\n", argv[1]); return 1;
    }

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "WSAStartup failed\n"); return 1;
    }

    if (load_messages(argv[2]) != 0) { WSACleanup(); return 1; }
    if (g_msg_cnt == 0) {
        fprintf(stderr, "no messages to send\n"); WSACleanup(); return 0;
    }

    SOCKADDR_IN dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_port   = htons((unsigned short)port);
    dst.sin_addr.s_addr = inet_addr(ip);
    if (dst.sin_addr.s_addr == INADDR_NONE) {
        fprintf(stderr, "error: invalid IP: %s\n", ip); WSACleanup(); return 1;
    }

    SOCKET s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s == INVALID_SOCKET) {
        fprintf(stderr, "socket err: %d\n", WSAGetLastError()); WSACleanup(); return 1;
    }

    int target = g_msg_cnt < TARGET_ACK ? g_msg_cnt : TARGET_ACK;
    int round = 0;
    while (count_acked() < target) {
        int s_cnt = send_unacked(s, &dst);
        if (s_cnt < 0) break;
        wait_and_collect_acks(s);
        printf("round %d: sent %d, acked %d/%d\n",
               ++round, s_cnt, count_acked(), target);
        if (round > 1000) {        // защита от бесконечного цикла при отсутствии сервера
            fprintf(stderr, "giving up: server not responding\n");
            break;
        }
    }

    closesocket(s);
    WSACleanup();
    printf("done: acked %d/%d in %d rounds\n", count_acked(), g_msg_cnt, round);
    return 0;
}
