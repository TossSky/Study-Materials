// Lab 3 OS, variant 1: parallel partition counting
// OS: Linux, pthreads. Sync: POSIX unnamed semaphores only.
// Author: Totskij V., gr. 5151003/40001

#include <pthread.h>
#include <semaphore.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <fstream>
#include <ctime>
#include <algorithm>

struct Task {
    int rem;
    int max_part;
};

static int g_T = 0;
static int g_N = 0;

static std::vector<Task> g_tasks;
static volatile int g_next_task = 0;

static sem_t g_sem_avail;
static sem_t g_sem_queue;
static sem_t g_sem_total;

static volatile uint64_t g_total = 0;

static uint64_t count_local(int rem, int max_part)
{
    if (rem == 0) return 1;
    uint64_t s = 0;
    int top = rem < max_part ? rem : max_part;
    for (int p = top; p >= 1; --p)
        s += count_local(rem - p, p);
    return s;
}

static void* worker(void* arg)
{
    int idx = (int)(long)arg;
    (void)idx;
    while (true) {
        sem_wait(&g_sem_avail);

        sem_wait(&g_sem_queue);
        int my = g_next_task;
        bool got = my < (int)g_tasks.size();
        if (got) g_next_task = my + 1;
        sem_post(&g_sem_queue);

        if (!got) break;

        Task t = g_tasks[my];
        uint64_t c = count_local(t.rem, t.max_part);

        sem_wait(&g_sem_total);
        g_total += c;
        sem_post(&g_sem_total);
    }
    return NULL;
}

static unsigned long long to_ms(const struct timespec& tm)
{
    return (unsigned long long)tm.tv_sec * 1000ULL +
           (unsigned long long)tm.tv_nsec / 1000000ULL;
}

int main()
{
    std::ifstream fin("input.txt");
    if (!fin) {
        std::fprintf(stderr, "cannot open input.txt\n");
        return 1;
    }
    fin >> g_T >> g_N;
    fin.close();

    if (g_T < 1) g_T = 1;
    if (g_N < 2) {
        std::ofstream fo("output.txt");
        fo << g_T << "\n" << g_N << "\n" << 0 << "\n";
        fo.close();
        std::ofstream ft("time.txt");
        ft << 0 << "\n";
        ft.close();
        return 0;
    }

    sem_init(&g_sem_avail, 0, 0);
    sem_init(&g_sem_queue, 0, 1);
    sem_init(&g_sem_total, 0, 1);

    std::vector<pthread_t> tids(g_T);
    for (int k = 0; k < g_T; ++k) {
        if (pthread_create(&tids[k], NULL, worker, (void*)(long)k) != 0) {
            std::fprintf(stderr, "pthread_create failed for %d\n", k);
            return 2;
        }
    }

    struct timespec t_start, t_end;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    g_tasks.reserve(g_N - 1);
    for (int p = 1; p <= g_N - 1; ++p) {
        Task t;
        t.rem = g_N - p;
        t.max_part = p;
        g_tasks.push_back(t);
    }
    for (int i = 0; i < (int)g_tasks.size(); ++i)
        sem_post(&g_sem_avail);
    for (int k = 0; k < g_T; ++k)
        sem_post(&g_sem_avail);

    for (int k = 0; k < g_T; ++k)
        pthread_join(tids[k], NULL);

    clock_gettime(CLOCK_MONOTONIC, &t_end);

    sem_destroy(&g_sem_avail);
    sem_destroy(&g_sem_queue);
    sem_destroy(&g_sem_total);

    std::ofstream fo("output.txt");
    fo << g_T << "\n" << g_N << "\n" << g_total << "\n";
    fo.close();

    unsigned long long ms = to_ms(t_end) - to_ms(t_start);
    std::ofstream ft("time.txt");
    ft << ms << "\n";
    ft.close();

    return 0;
}
