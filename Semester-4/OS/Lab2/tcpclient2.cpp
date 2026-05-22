#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static const int   MAX_CONNECT_ATTEMPTS = 10;
static const int   RECONNECT_DELAY_MS   = 100;
static const int   PHONE_LEN            = 12;
static const int   HEAD_SZ              = 4 + PHONE_LEN + PHONE_LEN + 3;
static const char* MODE_GET             = "get";

// Сон в миллисекундах.
static void sleep_ms(int ms)
{
    struct timespec ts;
    ts.tv_sec  = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, 0);
}

// Парсинг аргумента "IP:PORT".
static int parse_endpoint(const char* arg, char* ip, int ip_sz, int* port)
{
    const char* colon = strchr(arg, ':');
    if (!colon) return -1;
    int n = (int)(colon - arg);
    if (n <= 0 || n >= ip_sz) return -1;
    memcpy(ip, arg, n);
    ip[n] = 0;
    *port = atoi(colon + 1);
    return (*port > 0 && *port <= 65535) ? 0 : -1;
}

// Установка соединения с повторами.
static int connect_with_retry(const char* ip, int port)
{
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons((unsigned short)port);
    if (inet_aton(ip, &addr.sin_addr) == 0) {
        fprintf(stderr, "error: invalid IP: %s\n", ip);
        return -1;
    }
    for (int i = 0; i < MAX_CONNECT_ATTEMPTS; ++i) {
        int s = socket(AF_INET, SOCK_STREAM, 0);
        if (s < 0) { sleep_ms(RECONNECT_DELAY_MS); continue; }
        if (connect(s, (struct sockaddr*)&addr, sizeof(addr)) == 0) return s;
        close(s);
        sleep_ms(RECONNECT_DELAY_MS);
    }
    fprintf(stderr, "error: failed to connect to %s:%d\n", ip, port);
    return -1;
}

// Отправка всех данных.
static int send_all(int s, const void* buf, int len)
{
    const char* p = (const char*)buf;
    int sent = 0;
    while (sent < len) {
        int n = send(s, p + sent, len - sent, MSG_NOSIGNAL);
        if (n <= 0) { if (errno == EINTR) continue; return -1; }
        sent += n;
    }
    return 0;
}

// Дозапись принятых байт в накопительный буфер. 0 при закрытии соединения.
static int recv_some(int s, char* buf, int max_len)
{
    while (1) {
        int n = recv(s, buf, max_len, 0);
        if (n < 0 && errno == EINTR) continue;
        return n;
    }
}

// Запись одного сообщения в выходной файл.
static void write_message(FILE* f, const char* server_ep,
                          const char* phone1, const char* phone2,
                          unsigned char h, unsigned char m, unsigned char s,
                          const char* text)
{
    fprintf(f, "%s %.*s %.*s %02u:%02u:%02u %s\n",
            server_ep, PHONE_LEN, phone1, PHONE_LEN, phone2,
            (unsigned)h, (unsigned)m, (unsigned)s, text);
}

// Парсинг очередного сообщения из накопительного буфера.
// Возвращает: 1 - извлечено и записано, 0 - данных мало, -1 - ошибка.
static int try_extract_and_write(char* buf, int* buf_len, FILE* f, const char* server_ep)
{
    if (*buf_len < HEAD_SZ) return 0;
    int term = -1;
    for (int i = HEAD_SZ; i < *buf_len; ++i)
        if (buf[i] == 0) { term = i; break; }
    if (term < 0) return 0;

    const char*   phone1 = buf + 4;
    const char*   phone2 = buf + 4 + PHONE_LEN;
    unsigned char h      = (unsigned char)buf[4 + PHONE_LEN + PHONE_LEN];
    unsigned char m      = (unsigned char)buf[4 + PHONE_LEN + PHONE_LEN + 1];
    unsigned char s      = (unsigned char)buf[4 + PHONE_LEN + PHONE_LEN + 2];
    const char*   text   = buf + HEAD_SZ;

    write_message(f, server_ep, phone1, phone2, h, m, s, text);

    int consumed = term + 1;
    int rest     = *buf_len - consumed;
    if (rest > 0) memmove(buf, buf + consumed, rest);
    *buf_len = rest;
    return 1;
}

int main(int argc, char** argv)
{
    if (argc != 4 || strcmp(argv[2], "get") != 0) {
        fprintf(stderr, "Usage: %s IP:PORT get FILENAME\n", argv[0]);
        return 1;
    }
    char ip[64];
    int  port = 0;
    if (parse_endpoint(argv[1], ip, sizeof(ip), &port) != 0) {
        fprintf(stderr, "error: invalid endpoint: %s\n", argv[1]);
        return 1;
    }

    int sock = connect_with_retry(ip, port);
    if (sock < 0) return 1;

    if (send_all(sock, MODE_GET, 3) != 0) {
        fprintf(stderr, "error: failed to send 'get'\n");
        close(sock); return 1;
    }

    FILE* out = fopen(argv[3], "w");
    if (!out) { fprintf(stderr, "error: cannot open %s\n", argv[3]); close(sock); return 1; }

    static const int CAP = 65536;
    char* buf = (char*)malloc(CAP);
    int   buf_len = 0;
    int   cnt = 0;
    char  server_ep[80];
    snprintf(server_ep, sizeof(server_ep), "%s:%d", ip, port);

    while (1) {
        int n = recv_some(sock, buf + buf_len, CAP - buf_len);
        if (n == 0) break;
        if (n < 0) { fprintf(stderr, "recv err: %d\n", errno); break; }
        buf_len += n;
        while (try_extract_and_write(buf, &buf_len, out, server_ep) == 1) ++cnt;
        if (buf_len == CAP) {
            fprintf(stderr, "error: message too large\n");
            break;
        }
    }

    free(buf);
    fclose(out);
    close(sock);
    printf("done: %d messages written to %s\n", cnt, argv[3]);
    return 0;
}
