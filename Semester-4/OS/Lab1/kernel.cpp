// Команды: info, clear, shutdown, nsconv, posixtime, wintime.

typedef unsigned char      u8;
typedef unsigned short     u16;
typedef unsigned int       u32;
typedef unsigned long long u64;
typedef long long          s64;

// Точка входа ядра: лежит первой в секции .text.entry, прыгает в kmain.
extern "C" __attribute__((naked, section(".text.entry"))) void _start()
{
    asm volatile("jmp kmain");
}

extern "C" {

    // Беззнаковое 64-битное деление с остатком (long division). Нужно gcc для u64 / и %.
    u64 __udivmoddi4(u64 num, u64 den, u64* rem_out)
    {
        u64 q = 0, r = 0;
        for (int i = 63; i >= 0; --i) {
            r = (r << 1) | ((num >> i) & 1);
            if (r >= den) { r -= den; q |= (u64)1 << i; }
        }
        if (rem_out) *rem_out = r;
        return q;
    }

    // Беззнаковое 64-битное деление.
    u64 __udivdi3(u64 a, u64 b) { return __udivmoddi4(a, b, 0); }

    // Беззнаковый 64-битный остаток от деления.
    u64 __umoddi3(u64 a, u64 b) { u64 r; __udivmoddi4(a, b, &r); return r; }

    // Заполнение блока памяти байтом (для зануления статических массивов компилятором).
    void* memset(void* p, int c, unsigned n)
    {
        u8* d = (u8*)p; while (n--) *d++ = (u8)c; return p;
    }

} // extern "C"

// Чтение байта из порта ввода-вывода.
static inline u8 inb(u16 port)
{
    u8 v; 
    asm volatile("inb %1,%0" : "=a"(v) : "Nd"(port)); 
    return v;
}

// Запись байта в порт ввода-вывода.
static inline void outb(u16 port, u8 val)
{
    asm volatile("outb %0,%1" : : "a"(val), "Nd"(port));
}

// Запись слова (2 байта) в порт ввода-вывода (нужно для shutdown).
static inline void outw(u16 port, u16 val)
{
    asm volatile("outw %0,%1" : : "a"(val), "Nd"(port));
}

// Лексикографическое сравнение двух C-строк (аналог strcmp).
static int seq(const char* a, const char* b)
{
    while (*a && *a == *b) { ++a; ++b; }
    return (u8)*a - (u8)*b;
}

#define VIDEO    ((volatile u8*)0xB8000)
#define W        80
#define H        25
#define CRT_PORT 0x3D4

static int cur_row     = 0;
static int cur_col     = 0;
static u8  g_color     = 0x07;
static u8  g_color_idx = 0;

// Установка аппаратного курсора через CRTC-регистры (0x0E/0x0F порта 0x3D4).
static void update_cursor()
{
    u16 pos = (u16)(cur_row * W + cur_col);
    outb(CRT_PORT, 0x0F); 
    outb(CRT_PORT + 1, (u8)(pos & 0xFF));

    outb(CRT_PORT, 0x0E); 
    outb(CRT_PORT + 1, (u8)((pos >> 8) & 0xFF));
}

// Очистка всего экрана пробелами с текущим цветом.
static void cls()
{
    for (int i = 0; i < W * H; ++i) {
        VIDEO[i * 2]     = ' ';
        VIDEO[i * 2 + 1] = g_color;
    }
    cur_row = cur_col = 0;
    update_cursor();
}

// Сдвиг экрана на одну строку вверх.
static void scroll_up()
{
    for (int i = 0; i < (H - 1) * W * 2; ++i)
        VIDEO[i] = VIDEO[i + W * 2];
    for (int i = 0; i < W; ++i) {
        VIDEO[(H - 1) * W * 2 + i * 2]     = ' ';
        VIDEO[(H - 1) * W * 2 + i * 2 + 1] = g_color;
    }
}

// Перевод строки с автоскроллом при переполнении нижней границы.
static void newline()
{
    cur_col = 0;
    if (++cur_row >= H) { scroll_up(); cur_row = H - 1; }
}

// Вывод одного символа в позицию курсора.
static void putc(char c)
{
    if (c == '\n') 
    { 
        newline(); 
        update_cursor(); 
        return; 
    }

    int pos = (cur_row * W + cur_col) * 2;
    VIDEO[pos] = (u8)c;
    VIDEO[pos + 1] = g_color;

    if (++cur_col >= W) newline();
    update_cursor();
}

// Стирание одного символа слева от курсора (Backspace).
static void backspace_visual()
{
    if (cur_col == 0 && cur_row == 0) return;

    if (cur_col == 0) 
    { 
        --cur_row; 
        cur_col = W - 1; 
    }
    else 
    { 
        --cur_col; 
    }

    int pos = (cur_row * W + cur_col) * 2;
    VIDEO[pos]     = ' ';
    VIDEO[pos + 1] = g_color;
    update_cursor();
}

// Вывод 0-терминированной строки.
static void puts(const char* s) 
{ 
    while (*s) putc(*s++); 
}

// Вывод беззнакового 64-битного числа в системе счисления base (2..36).
static void put_u64(u64 v, int base)
{
    char buf[68];
    int  i = 0;
    if (v == 0) { putc('0'); return; }
    while (v) {
        u64 d = v % (u64)base;
        buf[i++] = d < 10 ? (char)('0' + d) : (char)('a' + d - 10);
        v /= (u64)base;
    }
    while (i--) putc(buf[i]);
}

// Вывод беззнакового 32-битного числа с ведущими нулями до ширины width (для даты).
static void put_u32_pad(u32 v, int width)
{
    char buf[12];
    int  i = 0;
    if (v == 0) buf[i++] = '0';
    while (v) { buf[i++] = (char)('0' + v % 10); v /= 10; }
    while (i < width) buf[i++] = '0';
    while (i--) putc(buf[i]);
}

#define IDT_TYPE_INTR 0x0E
#define GDT_CS        0x08

struct idt_entry {
    u16 base_lo;
    u16 segm_sel;
    u8  always0;
    u8  flags;
    u16 base_hi;
} __attribute__((packed));

struct idt_ptr {
    u16 limit;
    u32 base;
} __attribute__((packed));

static idt_entry g_idt[256];
static idt_ptr   g_idtp;

// Заглушка-обработчик: ничего не делает, корректно возвращается через iret.
extern "C" __attribute__((naked)) void default_handler()
{
    asm volatile("pusha\n popa\n iret\n");
}

extern "C" void keyb_process();

// Обработчик IRQ1 (клавиатура): чтение скан-кода + EOI на PIC1.
extern "C" __attribute__((naked)) void keyb_handler()
{
    asm volatile(
        "pusha\n"
        "call keyb_process\n"
        "movb $0x20, %al\n"
        "outb %al, $0x20\n"
        "popa\n"
        "iret\n"
    );
}

typedef void (*intr_fn)();

// Регистрация одного дескриптора прерывания в таблице IDT.
static void intr_reg(int num, u16 segm, u8 flags, intr_fn fn)
{
    u32 a = (u32)fn;
    g_idt[num].base_lo  = (u16)(a & 0xFFFF);
    g_idt[num].base_hi  = (u16)(a >> 16);
    g_idt[num].segm_sel = segm;
    g_idt[num].always0  = 0;
    g_idt[num].flags    = flags;
}

// Заполнение IDT заглушками, регистрация обработчика клавиатуры.
static void intr_init()
{
    for (int i = 0; i < 256; ++i)
        intr_reg(i, GDT_CS, 0x80 | IDT_TYPE_INTR, default_handler);
    intr_reg(0x09, GDT_CS, 0x80 | IDT_TYPE_INTR, keyb_handler);
}

// Загрузка IDT в IDTR, маска PIC только под клавиатуру, sti.
static void intr_start()
{
    g_idtp.base  = (u32)&g_idt[0];
    g_idtp.limit = (u16)(sizeof(g_idt) - 1);
    asm volatile("lidt %0" : : "m"(g_idtp));
    outb(0x21, 0xFF ^ 0x02);    // открыто только IRQ1
    outb(0xA1, 0xFF);
    asm volatile("sti");
}

// Таблица скан-кодов PS/2 (set 1) без Shift.
static const char SC_NORM[128] = {
    0,    0x1B, '1', '2', '3', '4', '5', '6',
    '7',  '8',  '9', '0', '-', '=', '\b','\t',
    'q',  'w',  'e', 'r', 't', 'y', 'u', 'i',
    'o',  'p',  '[', ']', '\n', 0,  'a', 's',
    'd',  'f',  'g', 'h', 'j', 'k', 'l', ';',
    '\'', '`',  0,   '\\','z', 'x', 'c', 'v',
    'b',  'n',  'm', ',', '.', '/', 0,   '*',
    0,    ' ',  0
};

// Таблица скан-кодов с зажатым Shift (для заглавных латинских букв).
static const char SC_SHIFT[128] = {
    0,    0x1B, '!', '@', '#', '$', '%', '^',
    '&',  '*',  '(', ')', '_', '+', '\b','\t',
    'Q',  'W',  'E', 'R', 'T', 'Y', 'U', 'I',
    'O',  'P',  '{', '}', '\n', 0,  'A', 'S',
    'D',  'F',  'G', 'H', 'J', 'K', 'L', ':',
    '"',  '~',  0,   '|', 'Z', 'X', 'C', 'V',
    'B',  'N',  'M', '<', '>', '?', 0,   '*',
    0,    ' ',  0
};

#define CMD_MAX 40

static volatile bool g_cmd_ready = false;
static char          g_cmd[CMD_MAX + 2];
static int           g_cmd_len   = 0;
static bool          g_shift     = false;

// Фильтр допустимых для ввода символов согласно методичке.
static bool allowed(char c)
{
    if (c >= 'a' && c <= 'z') return true;
    if (c >= 'A' && c <= 'Z') return true;
    if (c >= '0' && c <= '9') return true;
    return c == ' ' || c == '+' || c == '-' || c == '*' || c == '/';
}

// Обработка одного скан-кода: Shift, Backspace, Enter, ограничение длины.
extern "C" void keyb_process()
{
    if (!(inb(0x64) & 0x01)) return;
    u8 sc = inb(0x60);

    if (sc == 0x2A || sc == 0x36) { g_shift = true;  return; }
    if (sc == 0xAA || sc == 0xB6) { g_shift = false; return; }
    if (sc & 0x80) return;
    if (g_cmd_ready) return;

    char c = (g_shift ? SC_SHIFT : SC_NORM)[sc];
    if (!c) return;

    if (c == '\b') {
        if (g_cmd_len > 0) { --g_cmd_len; backspace_visual(); }
        return;
    }
    if (c == '\n') {
        g_cmd[g_cmd_len] = 0;
        putc('\n');
        g_cmd_ready = true;
        return;
    }
    if (!allowed(c))          return;
    if (g_cmd_len >= CMD_MAX) return;
    g_cmd[g_cmd_len++] = c;
    putc(c);
}

struct Args {
    const char* argv[6];
    int         argc;
    char        buf[CMD_MAX + 2];
};

// Разбор командной строки на argv/argc (разделитель — пробел).
static void parse_args(const char* line, Args& a)
{
    a.argc = 0;
    int n = 0;
    while (line[n]) { a.buf[n] = line[n]; ++n; }
    a.buf[n] = 0;
    int i = 0;
    while (i < n && a.argc < 6) {
        while (i < n && a.buf[i] == ' ') a.buf[i++] = 0;
        if (i >= n) break;
        a.argv[a.argc++] = &a.buf[i];
        while (i < n && a.buf[i] != ' ') ++i;
    }
}

enum ParseRes { PR_OK = 0, PR_EMPTY = 1, PR_OVER = 2, PR_BAD_SYM = 3 };

// Парсинг беззнакового u64 из строки в системе счисления base (2..36) с overflow-check.
static int parse_u64(const char* s, int base, u64& out, char* bad_sym)
{
    if (!s || !*s) return PR_EMPTY;
    u64       r    = 0;
    const u64 maxv = ~(u64)0;
    for (const char* p = s; *p; ++p) {
        char c = *p;
        int  d;
        if      (c >= '0' && c <= '9') d = c - '0';
        else if (c >= 'a' && c <= 'z') d = 10 + (c - 'a');
        else { if (bad_sym) *bad_sym = c; return PR_BAD_SYM; }
        if (d >= base) { if (bad_sym) *bad_sym = c; return PR_BAD_SYM; }
        if (r > (maxv - (u64)d) / (u64)base) return PR_OVER;
        r = r * (u64)base + (u64)d;
    }
    out = r;
    return PR_OK;
}

static const char* COLOR_NAMES[6] =
    { "gray", "white", "yellow", "blue", "red", "green" };

// Команда info: данные об авторе, средствах разработки и параметре загрузчика.
static void cmd_info()
{
    puts("ConvertOS v0.1. Author: Totskiy Vjatseslav, gr.5151003/40001, SPbPU, 2026\n");
    puts("Bootloader: YASM (Intel syntax). Kernel: g++ (gcc).\n");
    puts("Bootloader parameters: ");
    puts(g_color_idx < 6 ? COLOR_NAMES[g_color_idx] : "?");
    puts(" color.\n");
}

// Команда shutdown: запись в порты выключения для QEMU 
static void cmd_shutdown()
{
    puts("Powering off...\n");
    outw(0x604,  0x2000);
    outw(0xB004, 0x2000);
    outw(0x4004, 0x3400);
    asm volatile("cli; hlt");
    for (;;) asm volatile("hlt");
}

// Команда nsconv: перевод числа из исходной СС в конечную (обе 2..36).
static void cmd_nsconv(const Args& a)
{
    if (a.argc != 4) { puts("error: usage: nsconv N src dst\n"); return; }
    u64 src, dst;
    if (parse_u64(a.argv[2], 10, src, 0) != PR_OK || src < 2 || src > 36 ||
        parse_u64(a.argv[3], 10, dst, 0) != PR_OK || dst < 2 || dst > 36) {
        puts("error: base must be 2..36\n"); return;
    }
    u64  v;
    char bad = 0;
    int  r   = parse_u64(a.argv[1], (int)src, v, &bad);
    if (r == PR_EMPTY)   { puts("error: invalid number\n"); return; }
    if (r == PR_BAD_SYM) { puts("error: invalid symbol: "); putc(bad); putc('\n'); return; }
    if (r == PR_OVER)    { puts("error: int overflow\n"); return; }
    if (v > 0xFFFFFFFFULL) { puts("error: int overflow\n"); return; }
    put_u64(v, (int)dst);
    putc('\n');
}

// Проверка високосного года по григорианскому правилу.
static bool is_leap(int y)
{
    return (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
}

// Число дней в месяце с учётом високосного февраля.
static int days_in_month(int m, int y)
{
    static const int d[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (m == 2 && is_leap(y)) return 29;
    return d[m - 1];
}

// Печать DD.MM.YYYY HH:MM:SS из секунд от Unix-эпохи.
static void print_unix_date(u64 secs)
{
    u64 days = secs / 86400;
    u64 sod  = secs % 86400;
    int h = (int)(sod / 3600);
    int m = (int)((sod % 3600) / 60);
    int s = (int)(sod % 60);

    int y = 1970;
    while (1) {
        int dy = is_leap(y) ? 366 : 365;
        if (days < (u64)dy) break;
        days -= dy; ++y;
    }
    int mo = 1;
    while (mo <= 12) {
        int dm = days_in_month(mo, y);
        if (days < (u64)dm) break;
        days -= dm; ++mo;
    }
    int d = (int)days + 1;

    put_u32_pad((u32)d,  2); putc('.');
    put_u32_pad((u32)mo, 2); putc('.');
    put_u32_pad((u32)y,  4); putc(' ');
    put_u32_pad((u32)h,  2); putc(':');
    put_u32_pad((u32)m,  2); putc(':');
    put_u32_pad((u32)s,  2); putc('\n');
}

// Команда posixtime: аргумент — Unix timestamp в секундах.
static void cmd_posixtime(const Args& a)
{
    if (a.argc != 2) { puts("error: usage: posixtime N\n"); return; }
    u64 v;
    if (parse_u64(a.argv[1], 10, v, 0) != PR_OK) {
        puts("error: invalid number\n"); return;
    }
    print_unix_date(v);
}

// Команда wintime: 64-битный FILETIME (100-нс интервалы от 01.01.1601 UTC).
static void cmd_wintime(const Args& a)
{
    if (a.argc != 2) { puts("error: usage: wintime N\n"); return; }
    u64 v;
    if (parse_u64(a.argv[1], 10, v, 0) != PR_OK) {
        puts("error: invalid number\n"); return;
    }
    u64 secs1601 = v / 10000000ULL;
    const u64 EPOCH_DIFF = 11644473600ULL; // секунд между 1601-01-01 и 1970-01-01
    if (secs1601 < EPOCH_DIFF) { puts("error: date before 1970\n"); return; }
    print_unix_date(secs1601 - EPOCH_DIFF);
}

// Индекс единицы измерения размера: b/kb/mb/gb/tb -> 0..4, иначе -1.
static int unit_idx(const char* s)
{
    if (seq(s, "b")  == 0) return 0;
    if (seq(s, "kb") == 0) return 1;
    if (seq(s, "mb") == 0) return 2;
    if (seq(s, "gb") == 0) return 3;
    if (seq(s, "tb") == 0) return 4;
    return -1;
}

// Имя единицы по индексу 0..4.
static const char* unit_name(int i)
{
    static const char* n[] = {"b","kb","mb","gb","tb"};
    return n[i];
}

// 1024^n для перевода между единицами размера.
static u64 pow1024(int n) { u64 r = 1; while (n--) r *= 1024ULL; return r; }

// Команда szconv (доп. задание): перевод размера b/kb/mb/gb/tb, 2 знака после запятой.
static void cmd_szconv(const Args& a)
{
    if (a.argc != 4) { puts("error: usage: szconv N src dst\n"); return; }
    int s_u = unit_idx(a.argv[2]);
    int d_u = unit_idx(a.argv[3]);
    if (s_u < 0 || d_u < 0) { puts("error: invalid size unit\n"); return; }

    u64  n;
    char bad = 0;
    int  r   = parse_u64(a.argv[1], 10, n, &bad);
    if (r == PR_EMPTY || r == PR_BAD_SYM) {
        puts("error: invalid size: "); puts(a.argv[1]); putc('\n'); return;
    }
    if (r == PR_OVER) { puts("error: int overflow\n"); return; }

    if (s_u >= d_u) {
        int diff = s_u - d_u;
        u64 mul  = pow1024(diff);
        if (mul != 0 && n > (~(u64)0) / mul) { puts("error: int overflow\n"); return; }
        u64 v = n * mul;
        put_u64(v, 10); puts(".00 "); puts(unit_name(d_u)); putc('\n');
    } else {
        int diff = d_u - s_u;
        u64 div  = pow1024(diff);
        u64 ip   = n / div;
        u64 rm   = n - ip * div;
        u64 fp   = (rm * 100ULL) / div;
        put_u64(ip, 10); putc('.');
        if (fp < 10) putc('0');
        put_u64(fp, 10);
        putc(' '); puts(unit_name(d_u)); putc('\n');
    }
}

// Печать приглашения для ввода команды.
static void prompt() { puts("# "); }

// Поиск и вызов обработчика команды по первому argv.
static void execute(const char* line)
{
    if (!line[0]) return;
    Args a;
    parse_args(line, a);
    if (a.argc == 0) return;
    const char* c = a.argv[0];

    if (seq(c, "info")      == 0) { cmd_info();        return; }
    if (seq(c, "clear")     == 0) { cls();             return; }
    if (seq(c, "shutdown")  == 0) { cmd_shutdown();    return; }
    if (seq(c, "nsconv")    == 0) { cmd_nsconv(a);     return; }
    if (seq(c, "posixtime") == 0) { cmd_posixtime(a);  return; }
    if (seq(c, "wintime")   == 0) { cmd_wintime(a);    return; }
    if (seq(c, "szconv")    == 0) { cmd_szconv(a);     return; }
    puts("Error: command not recognized\n");
}

// Точка входа ядра: применить параметры загрузчика, прерывания, REPL.
extern "C" int kmain()
{
    g_color     = *(volatile u8*)0x7E00;
    g_color_idx = *(volatile u8*)0x7E01;
    if (g_color == 0)    g_color = 0x07;
    if (g_color_idx > 5) g_color_idx = 0;

    cls();
    puts("Welcome to ConvertOS!\n");
    intr_init();
    intr_start();
    prompt();

    while (1) {
        if (g_cmd_ready) {
            asm volatile("cli");
            char local[CMD_MAX + 2];
            int  ln = g_cmd_len;
            for (int i = 0; i <= ln; ++i) local[i] = g_cmd[i];
            g_cmd_len   = 0;
            g_cmd_ready = false;
            asm volatile("sti");
            execute(local);
            prompt();
        }
        asm volatile("hlt");
    }
}
