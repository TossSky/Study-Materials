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
static const char* MODE_PUT             = "put";

// Сон в миллисекундах через nanosleep (без зависимости от usleep/POSIX 200809).
static void sleep_ms(int ms)
{
    struct timespec ts;
    ts.tv_sec  = ms / 1000;
    ts.tv_nsec = (long)(ms % 1000) * 1000000L;
    nanosleep(&ts, 0);
}

// Парсинг аргумента "IP:PORT" в отдельные поля.
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

// Установка TCP-соединения. До 10 попыток с паузой 100 мс при неудаче.
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
    fprintf(stderr, "error: failed to connect to %s:%d after %d attempts\n",
            ip, port, MAX_CONNECT_ATTEMPTS);
    return -1;
}

// Отправка ровно len байт в сокет (учёт частичной записи).
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

// Чтение ровно len байт из сокета.
static int recv_all(int s, void* buf, int len)
{
    char* p = (char*)buf;
    int got = 0;
    while (got < len) {
        int n = recv(s, p + got, len - got, 0);
        if (n == 0) return -1;
        if (n < 0) { if (errno == EINTR) continue; return -1; }
        got += n;
    }
    return 0;
}

// Проверка телефона: 12 символов, начинается с '+', далее цифра '7' и 10 цифр.
static int is_phone(const char* s)
{
    if (s[0] != '+' || s[1] != '7') return 0;
    for (int i = 2; i < PHONE_LEN; ++i)
        if (s[i] < '0' || s[i] > '9') return 0;
    return 1;
}

// Парсинг времени hh:mm:ss с проверкой диапазонов.
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

// Формирование бинарного сообщения протокола в буфере out.
// Возвращает реальную длину сообщения или -1 при ошибке разбора строки.
static int build_message(const char* line, unsigned int idx, char* out, int out_sz)
{
    const char* p = line;
    while (*p == ' ' || *p == '\t') ++p;
    if (!*p) return -1;

    char phone1[PHONE_LEN + 1], phone2[PHONE_LEN + 1], tm[16];
    if (sscanf(p, "%12s %12s %15s", phone1, phone2, tm) != 3) return -1;
    if (!is_phone(phone1) || !is_phone(phone2)) return -1;

    unsigned char h, m, s;
    if (parse_time(tm, &h, &m, &s) != 0) return -1;

    // Найти начало текста сообщения: пропустить 3 поля и 3 разделителя-пробела.
    const char* msg = p;
    int spaces = 0;
    while (*msg && spaces < 3) {
        if (*msg == ' ') ++spaces;
        ++msg;
    }
    if (spaces < 3) return -1;
    int msg_len = (int)strlen(msg);

    int total = 4 + PHONE_LEN + PHONE_LEN + 3 + msg_len + 1;
    if (total > out_sz) return -1;

    unsigned int idx_be = htonl(idx);
    int off = 0;
    memcpy(out + off, &idx_be, 4); off += 4;
    memcpy(out + off, phone1, PHONE_LEN); off += PHONE_LEN;
    memcpy(out + off, phone2, PHONE_LEN); off += PHONE_LEN;
    out[off++] = (char)h;
    out[off++] = (char)m;
    out[off++] = (char)s;
    memcpy(out + off, msg, msg_len); off += msg_len;
    out[off++] = 0;
    return off;
}

// Чтение, разбор и отправка всех сообщений из файла. Возвращает кол-во отправленных.
static int send_messages(int sock, FILE* f)
{
    char line[2048];
    char msg[2048];
    int  idx       = 0;
    int  sent_cnt  = 0;
    while (fgets(line, sizeof(line), f)) {
        size_t n = strlen(line);
        while (n > 0 && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
        if (n == 0) { ++idx; continue; }

        int len = build_message(line, (unsigned int)idx, msg, sizeof(msg));
        ++idx;
        if (len < 0) {
            fprintf(stderr, "skip: invalid line\n");
            continue;
        }
        if (send_all(sock, msg, len) != 0) {
            fprintf(stderr, "error: send failed\n");
            return -1;
        }
        ++sent_cnt;
    }
    return sent_cnt;
}

// Чтение ровно cnt подтверждений "ok" (по 2 байта) от сервера.
static int recv_acks(int sock, int cnt)
{
    char buf[2];
    for (int i = 0; i < cnt; ++i) {
        if (recv_all(sock, buf, 2) != 0) {
            fprintf(stderr, "error: ack %d/%d not received\n", i + 1, cnt);
            return -1;
        }
        if (buf[0] != 'o' || buf[1] != 'k') {
            fprintf(stderr, "error: bad ack: %02x %02x\n",
                    (unsigned char)buf[0], (unsigned char)buf[1]);
            return -1;
        }
    }
    return 0;
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
        fprintf(stderr, "error: invalid endpoint: %s\n", argv[1]);
        return 1;
    }
    FILE* f = fopen(argv[2], "r");
    if (!f) { fprintf(stderr, "error: cannot open file %s\n", argv[2]); return 1; }

    int sock = connect_with_retry(ip, port);
    if (sock < 0) { fclose(f); return 1; }

    if (send_all(sock, MODE_PUT, 3) != 0) {
        fprintf(stderr, "error: failed to send mode\n");
        close(sock); fclose(f); return 1;
    }

    int sent_cnt = send_messages(sock, f);
    fclose(f);
    if (sent_cnt < 0) { close(sock); return 1; }

    int rc = recv_acks(sock, sent_cnt);
    close(sock);
    if (rc != 0) return 1;

    printf("done: %d messages sent\n", sent_cnt);
    return 0;
}
