#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/select.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define PHONE_LEN     12
#define HEAD_SZ       (4 + PHONE_LEN + PHONE_LEN + 3)
#define MAX_DGRAM     65507
#define MAX_PORTS     64
#define MAX_CLIENTS   256
#define MAX_PER_CLI   20             // лимит хранимых индексов в ответе
#define IDLE_TIMEOUT  30             // секунд

// Запись о клиенте: ID = ip+port, кольцевой буфер последних индексов, время.
struct Client {
    unsigned int  ip;                // BE
    unsigned short port;             // BE
    unsigned int  ids[MAX_PER_CLI];  // последние принятые индексы (новейший в конце)
    int           ids_cnt;
    time_t        last_seen;
    int           in_use;
};

static Client g_clients[MAX_CLIENTS];

// Перевод сокета в неблокирующий режим.
static int set_nonblock(int s)
{
    int fl = fcntl(s, F_GETFL, 0);
    return fcntl(s, F_SETFL, fl | O_NONBLOCK);
}

// Поиск клиента по адресу+порту. Возвращает индекс или -1.
static int find_client(unsigned int ip, unsigned short port)
{
    for (int i = 0; i < MAX_CLIENTS; ++i)
        if (g_clients[i].in_use && g_clients[i].ip == ip && g_clients[i].port == port)
            return i;
    return -1;
}

// Создание новой записи о клиенте. Возвращает индекс или -1 при переполнении.
static int add_client(unsigned int ip, unsigned short port)
{
    for (int i = 0; i < MAX_CLIENTS; ++i) {
        if (!g_clients[i].in_use) {
            memset(&g_clients[i], 0, sizeof(g_clients[i]));
            g_clients[i].in_use    = 1;
            g_clients[i].ip        = ip;
            g_clients[i].port      = port;
            g_clients[i].last_seen = time(0);
            return i;
        }
    }
    return -1;
}

// Удаление "молчаливых" клиентов (idle > IDLE_TIMEOUT секунд).
static void cleanup_idle()
{
    time_t now = time(0);
    for (int i = 0; i < MAX_CLIENTS; ++i) {
        if (g_clients[i].in_use && now - g_clients[i].last_seen > IDLE_TIMEOUT) {
            g_clients[i].in_use = 0;
            fprintf(stderr, "client removed: idle > %d sec\n", IDLE_TIMEOUT);
        }
    }
}

// Проверка, был ли уже принят такой индекс от клиента.
static int has_id(const Client* c, unsigned int idx)
{
    for (int i = 0; i < c->ids_cnt; ++i)
        if (c->ids[i] == idx) return 1;
    return 0;
}

// Добавление нового индекса (с вытеснением старейшего при переполнении).
static void push_id(Client* c, unsigned int idx)
{
    if (c->ids_cnt < MAX_PER_CLI) {
        c->ids[c->ids_cnt++] = idx;
    } else {
        memmove(&c->ids[0], &c->ids[1], sizeof(unsigned int) * (MAX_PER_CLI - 1));
        c->ids[MAX_PER_CLI - 1] = idx;
    }
}

// Запись одного валидного сообщения в msg.txt в текстовом формате.
static void log_message(unsigned int ip, unsigned short port, const char* dg, int dg_len)
{
    if (dg_len < HEAD_SZ + 1) return;
    int term = -1;
    for (int i = HEAD_SZ; i < dg_len; ++i)
        if (dg[i] == 0) { term = i; break; }
    if (term < 0) return;

    const char*   phone1 = dg + 4;
    const char*   phone2 = dg + 4 + PHONE_LEN;
    unsigned char h      = (unsigned char)dg[4 + PHONE_LEN + PHONE_LEN];
    unsigned char m      = (unsigned char)dg[4 + PHONE_LEN + PHONE_LEN + 1];
    unsigned char s      = (unsigned char)dg[4 + PHONE_LEN + PHONE_LEN + 2];

    FILE* f = fopen("msg.txt", "a");
    if (!f) return;
    unsigned int ip_h = ntohl(ip);
    fprintf(f, "%u.%u.%u.%u:%hu %.*s %.*s %02u:%02u:%02u %s\n",
            (ip_h >> 24) & 0xFF, (ip_h >> 16) & 0xFF,
            (ip_h >> 8)  & 0xFF,  ip_h & 0xFF,
            ntohs(port),
            PHONE_LEN, phone1, PHONE_LEN, phone2,
            (unsigned)h, (unsigned)m, (unsigned)s,
            dg + HEAD_SZ);
    fclose(f);
}

// Извлечение текста сообщения для проверки на "stop".
static int is_stop(const char* dg, int dg_len)
{
    if (dg_len < HEAD_SZ + 1) return 0;
    int term = -1;
    for (int i = HEAD_SZ; i < dg_len; ++i)
        if (dg[i] == 0) { term = i; break; }
    if (term < 0) return 0;
    int tlen = term - HEAD_SZ;
    return tlen == 4 && memcmp(dg + HEAD_SZ, "stop", 4) == 0;
}

// Сборка ответа: последние ids_cnt индексов (от нового к старому), не более 20.
static int build_ack(const Client* c, char* out, int out_sz)
{
    int n = c->ids_cnt < MAX_PER_CLI ? c->ids_cnt : MAX_PER_CLI;
    if (n * 4 > out_sz) n = out_sz / 4;
    int off = 0;
    for (int i = c->ids_cnt - 1; i >= 0 && off / 4 < n; --i) {
        unsigned int v = htonl(c->ids[i]);
        memcpy(out + off, &v, 4);
        off += 4;
    }
    return off;
}

// Обработка одной поступившей дейтаграммы.
// Возвращает 1, если принято сообщение "stop" (нужно завершить сервер).
static int process_datagram(int sock, char* dg, int dg_len,
                            const struct sockaddr_in* from)
{
    if (dg_len < HEAD_SZ + 1) {
        fprintf(stderr, "short datagram from %u: %d bytes\n",
                ntohs(from->sin_port), dg_len);
        return 0;
    }
    unsigned int idx;
    memcpy(&idx, dg, 4);
    idx = ntohl(idx);

    unsigned int   ip   = from->sin_addr.s_addr;
    unsigned short port = from->sin_port;

    int ci = find_client(ip, port);
    if (ci < 0) {
        ci = add_client(ip, port);
        if (ci < 0) { fprintf(stderr, "no free client slot\n"); return 0; }
    }
    Client* c = &g_clients[ci];
    c->last_seen = time(0);

    int stop_flag = 0;
    if (!has_id(c, idx)) {
        log_message(ip, port, dg, dg_len);
        push_id(c, idx);
        if (is_stop(dg, dg_len)) stop_flag = 1;
    }

    char ack[MAX_PER_CLI * 4];
    int  ack_len = build_ack(c, ack, sizeof(ack));
    if (ack_len > 0) {
        sendto(sock, ack, ack_len, 0, (const struct sockaddr*)from, sizeof(*from));
    }
    return stop_flag;
}

int main(int argc, char** argv)
{
    if (argc != 3) {
        fprintf(stderr, "Usage: %s PORT_FROM PORT_TILL\n", argv[0]);
        return 1;
    }
    int p_from = atoi(argv[1]);
    int p_till = atoi(argv[2]);
    if (p_from <= 0 || p_till < p_from || p_till - p_from + 1 > MAX_PORTS) {
        fprintf(stderr, "bad port range\n"); return 1;
    }

    int n_ports = p_till - p_from + 1;
    int socks[MAX_PORTS];
    int max_fd = 0;

    for (int i = 0; i < n_ports; ++i) {
        int s = socket(AF_INET, SOCK_DGRAM, 0);
        if (s < 0) { perror("socket"); return 1; }
        set_nonblock(s);
        int yes = 1;
        setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
        struct sockaddr_in a;
        memset(&a, 0, sizeof(a));
        a.sin_family      = AF_INET;
        a.sin_addr.s_addr = htonl(INADDR_ANY);
        a.sin_port        = htons((unsigned short)(p_from + i));
        if (bind(s, (struct sockaddr*)&a, sizeof(a)) < 0) {
            fprintf(stderr, "bind port %d failed: %s\n", p_from + i, strerror(errno));
            return 1;
        }
        socks[i] = s;
        if (s > max_fd) max_fd = s;
    }
    printf("listening UDP %d..%d\n", p_from, p_till);

    int stop_flag = 0;
    while (!stop_flag) {
        fd_set rfd;
        FD_ZERO(&rfd);
        for (int i = 0; i < n_ports; ++i) FD_SET(socks[i], &rfd);
        struct timeval tv = { 5, 0 };
        int r = select(max_fd + 1, &rfd, 0, 0, &tv);
        if (r < 0) { if (errno == EINTR) continue; perror("select"); break; }
        if (r == 0) { cleanup_idle(); continue; }

        for (int i = 0; i < n_ports && !stop_flag; ++i) {
            if (!FD_ISSET(socks[i], &rfd)) continue;
            for (;;) {
                char dg[MAX_DGRAM];
                struct sockaddr_in from;
                socklen_t flen = sizeof(from);
                int n = recvfrom(socks[i], dg, sizeof(dg), 0,
                                 (struct sockaddr*)&from, &flen);
                if (n < 0) {
                    if (errno == EAGAIN || errno == EWOULDBLOCK) break;
                    perror("recvfrom"); break;
                }
                if (process_datagram(socks[i], dg, n, &from)) {
                    stop_flag = 1;
                    break;
                }
            }
        }
        cleanup_idle();
    }

    for (int i = 0; i < n_ports; ++i) close(socks[i]);
    printf("server stopped\n");
    return 0;
}
