/* Консольный клиент для Windows.
   Взаимодействие с МК через виртуальный COM-порт (CH340/FT232 или simavr).
   Компиляция:  gcc -Wall pc_client.c rsa.c -o pc_client.exe
   Запуск:      pc_client.exe COM3                                        */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <windows.h>

#include "protocol.h"
#include "rsa.h"

static HANDLE hPort = INVALID_HANDLE_VALUE;

/* ---------- Serial I/O ---------- */
static int port_open(const char *name)
{
    char full[64];
    snprintf(full, sizeof(full), "\\\\.\\%s", name);
    hPort = CreateFileA(full, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                        OPEN_EXISTING, 0, NULL);
    if (hPort == INVALID_HANDLE_VALUE) return -1;

    DCB dcb = { .DCBlength = sizeof(dcb) };
    GetCommState(hPort, &dcb);
    dcb.BaudRate = CBR_9600;
    dcb.ByteSize = 8;
    dcb.Parity   = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    SetCommState(hPort, &dcb);

    COMMTIMEOUTS to = { MAXDWORD, 0, 5000, 0, 5000 };
    SetCommTimeouts(hPort, &to);
    return 0;
}

static void port_write(const uint8_t *buf, size_t n)
{
    DWORD w; WriteFile(hPort, buf, (DWORD)n, &w, NULL);
}
static void port_read(uint8_t *buf, size_t n)
{
    DWORD r, total = 0;
    while (total < n) {
        if (!ReadFile(hPort, buf + total, (DWORD)(n - total), &r, NULL) || r == 0) {
            fprintf(stderr, "[serial timeout]\n"); exit(2);
        }
        total += r;
    }
}
static void put8 (uint8_t v)  { port_write(&v, 1); }
static void put16(uint16_t v) { uint8_t b[2]={v>>8,v&0xFF}; port_write(b,2); }
static uint8_t  get8 (void)   { uint8_t  v; port_read(&v, 1); return v; }
static uint16_t get16(void)   { uint8_t  b[2]; port_read(b,2); return (b[0]<<8)|b[1]; }
static uint32_t get32(void)   { uint8_t  b[4]; port_read(b,4);
                                return ((uint32_t)b[0]<<24)|((uint32_t)b[1]<<16)|(b[2]<<8)|b[3]; }

/* ---------- Операции ---------- */
static void op_add_key(uint16_t n, uint16_t e, uint16_t d)
{
    put8(CMD_ADD_KEY); put16(n); put16(e); put16(d);
    uint8_t st = get8();
    if (st != ST_OK) { printf("ADD_KEY error: 0x%02X\n", st); return; }
    printf("Key added to slot %u\n", get8());
}

static void op_del_key(uint8_t slot)
{
    put8(CMD_DEL_KEY); put8(slot);
    uint8_t st = get8();
    if (st != ST_OK) { printf("DEL_KEY error: 0x%02X\n", st); return; }
    printf("Key in slot %u deleted\n", slot);
}

static void op_list(void)
{
    put8(CMD_LIST_KEYS);
    if (get8() != ST_OK) { printf("LIST error\n"); return; }
    uint8_t cnt = get8();
    printf("Keys in EEPROM: %u\n", cnt);
    for (uint8_t i = 0; i < cnt; i++) {
        uint16_t n = get16(), e = get16();
        printf("  [%u] n=%u e=%u\n", i, n, e);
    }
}

static void op_encrypt(const char *in, const char *out, uint16_t n, uint16_t e)
{
    FILE *fi = fopen(in, "rb"); if (!fi) { perror(in); return; }
    fseek(fi, 0, SEEK_END); long sz = ftell(fi); fseek(fi, 0, SEEK_SET);
    if (sz > 65535) { printf("file too large\n"); fclose(fi); return; }

    put8(CMD_ENCRYPT); put16(n); put16(e); put16((uint16_t)sz);
    uint8_t st = get8();
    if (st != ST_OK) { printf("ENCRYPT error: 0x%02X\n", st); fclose(fi); return; }

    FILE *fo = fopen(out, "wb");
    for (long i = 0; i < sz; i++) {
        uint8_t b = (uint8_t)fgetc(fi);
        put8(b);
        uint16_t c = get16();
        fputc((uint8_t)(c >> 8), fo);
        fputc((uint8_t)(c & 0xFF), fo);
    }
    fclose(fi); fclose(fo);
    printf("Encrypted %ld bytes -> %s (%ld bytes)\n", sz, out, sz * 2);
}

static void op_decrypt(const char *in, const char *out, uint16_t n, uint16_t e)
{
    FILE *fi = fopen(in, "rb"); if (!fi) { perror(in); return; }
    fseek(fi, 0, SEEK_END); long sz = ftell(fi); fseek(fi, 0, SEEK_SET);
    if (sz % 2) { printf("ciphertext must be even length\n"); fclose(fi); return; }
    uint16_t blocks = (uint16_t)(sz / 2);

    put8(CMD_DECRYPT); put16(n); put16(e); put16(blocks);
    uint8_t st = get8();
    if (st != ST_OK) { printf("DECRYPT error: 0x%02X\n", st); fclose(fi); return; }

    FILE *fo = fopen(out, "wb");
    for (uint16_t i = 0; i < blocks; i++) {
        uint8_t hi = (uint8_t)fgetc(fi), lo = (uint8_t)fgetc(fi);
        put8(hi); put8(lo);
        fputc(get8(), fo);
    }
    fclose(fi); fclose(fo);
    printf("Decrypted -> %s (%u bytes)\n", out, blocks);
}

static uint16_t file_hash_modn(const char *path, uint16_t n)
{
    FILE *f = fopen(path, "rb");
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *buf = (uint8_t*)malloc(sz);
    fread(buf, 1, sz, f); fclose(f);
    uint16_t h = crc16_ccitt(buf, sz) % n;
    free(buf);
    return h;
}

static void op_sign(const char *path, uint16_t n, uint16_t e)
{
    uint16_t h = file_hash_modn(path, n);
    put8(CMD_SIGN); put16(n); put16(e); put16(h);
    uint8_t st = get8();
    if (st != ST_OK) { printf("SIGN error: 0x%02X\n", st); return; }
    uint16_t s = get16();
    printf("hash=%u signature=%u\n", h, s);
}

static void op_verify(const char *path, uint16_t n, uint16_t e, uint16_t sig)
{
    uint16_t h = file_hash_modn(path, n);
    put8(CMD_VERIFY); put16(n); put16(e); put16(h); put16(sig);
    if (get8() != ST_OK) { printf("VERIFY error\n"); return; }
    printf("%s\n", get8() ? "SIGNATURE OK" : "SIGNATURE BAD");
}

static void op_stats(void)
{
    put8(CMD_GET_STATS);
    if (get8() != ST_OK) { printf("STATS error\n"); return; }
    uint32_t enc = get32(), dec = get32();
    uint16_t sg  = get16(), ch  = get16();
    printf("enc_len=%u dec_len=%u sign=%u check=%u\n", enc, dec, sg, ch);
}

/* ---------- main / меню ---------- */
static void usage(void) {
    puts("Commands:");
    puts("  add <n> <e> <d>     — записать ключ");
    puts("  del <slot>          — удалить ключ из слота");
    puts("  list                — список ключей");
    puts("  enc <in> <out> <n> <e>");
    puts("  dec <in> <out> <n> <e>");
    puts("  sign <file> <n> <e>");
    puts("  ver  <file> <n> <e> <sig>");
    puts("  stats");
    puts("  rstats              — обнулить статистику");
    puts("  quit");
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s COMx\n", argv[0]); return 1; }
    if (port_open(argv[1]) < 0) { fprintf(stderr, "cannot open %s\n", argv[1]); return 1; }
    printf("Connected to %s at 9600-8N1\n", argv[1]);
    usage();

    char line[256];
    while (printf("> "), fflush(stdout), fgets(line, sizeof(line), stdin)) {
        char cmd[16]; unsigned a, b, c; char p1[64], p2[64];
        if      (sscanf(line, "%15s", cmd) != 1) continue;
        else if (!strcmp(cmd, "quit")) break;
        else if (!strcmp(cmd, "list"))   op_list();
        else if (!strcmp(cmd, "stats"))  op_stats();
        else if (!strcmp(cmd, "rstats")) { put8(CMD_RESET_STATS); get8(); puts("ok"); }
        else if (!strcmp(cmd, "add")  && sscanf(line,"%*s %u %u %u", &a,&b,&c)==3)
            op_add_key((uint16_t)a,(uint16_t)b,(uint16_t)c);
        else if (!strcmp(cmd, "del")  && sscanf(line,"%*s %u", &a)==1)
            op_del_key((uint8_t)a);
        else if (!strcmp(cmd, "enc")  && sscanf(line,"%*s %63s %63s %u %u",p1,p2,&a,&b)==4)
            op_encrypt(p1,p2,(uint16_t)a,(uint16_t)b);
        else if (!strcmp(cmd, "dec")  && sscanf(line,"%*s %63s %63s %u %u",p1,p2,&a,&b)==4)
            op_decrypt(p1,p2,(uint16_t)a,(uint16_t)b);
        else if (!strcmp(cmd, "sign") && sscanf(line,"%*s %63s %u %u",p1,&a,&b)==3)
            op_sign(p1,(uint16_t)a,(uint16_t)b);
        else if (!strcmp(cmd, "ver")  && sscanf(line,"%*s %63s %u %u %u",p1,&a,&b,&c)==4)
            op_verify(p1,(uint16_t)a,(uint16_t)b,(uint16_t)c);
        else usage();
    }
    CloseHandle(hPort);
    return 0;
}
