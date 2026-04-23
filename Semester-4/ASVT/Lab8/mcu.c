/* Лабораторная работа 8, вариант 6а.
   Прошивка ATmega32 (F_CPU = 8 МГц). Криптосистема RSA.
   - UART 9600 8N1 — связь с ПК;
   - EEPROM — хранение нескольких троек (n, e, d) и статистики;
   - 7-сегментный индикатор — вывод E.xxx / d.xxx / S.xxx / C.xxx;
   - INT0 (кнопка на PD2) — циклическое переключение режима индикации. */

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/eeprom.h>
#include <stdint.h>
#include "rsa.h"
#include "protocol.h"

/* Задержка 2 мс реализована отдельной подпрограммой на ассемблере
   (см. delay_asm.S, вариант 6а). */
extern void delay_2ms_asm(void);

/* ==================== UART (9600 8N1 @ 8 МГц) ==================== */
#define UBRR_VAL 51   /* 8 000 000 / (16·9600) − 1 */

static void uart_init(void)
{
    UBRRH = 0;
    UBRRL = UBRR_VAL;
    UCSRB = (1 << RXEN) | (1 << TXEN);
    UCSRC = (1 << URSEL) | (1 << UCSZ1) | (1 << UCSZ0);
}

static uint8_t uart_get(void)
{
    while (!(UCSRA & (1 << RXC))) { }
    return UDR;
}

static void uart_put(uint8_t b)
{
    while (!(UCSRA & (1 << UDRE))) { }
    UDR = b;
}

static uint16_t uart_get16(void) {
    uint16_t hi = uart_get();
    uint16_t lo = uart_get();
    return (hi << 8) | lo;
}

static void uart_put16(uint16_t v) {
    uart_put((uint8_t)(v >> 8));
    uart_put((uint8_t)(v & 0xFF));
}

/* ==================== EEPROM: ключи и статистика ==================== */
typedef struct {
    uint16_t n, e, d;
    uint8_t  used;   /* 0xAA = слот занят, иначе свободен */
} KeyRec;

typedef struct {
    uint32_t enc_len;   /* суммарная длина зашифрованных файлов   */
    uint32_t dec_len;   /* суммарная длина расшифрованных файлов  */
    uint16_t sign_cnt;  /* число операций подписания              */
    uint16_t check_cnt; /* число операций проверки подписи        */
} Stats;

static KeyRec EEMEM ee_keys[MAX_KEYS];
static Stats  EEMEM ee_stats;

/* Поиск слота по паре (n, e). Возвращает индекс или −1. */
static int find_key(uint16_t n, uint16_t e, KeyRec *out)
{
    for (uint8_t i = 0; i < MAX_KEYS; i++) {
        KeyRec k;
        eeprom_read_block(&k, &ee_keys[i], sizeof(KeyRec));
        if (k.used == 0xAA && k.n == n && k.e == e) {
            if (out) *out = k;
            return i;
        }
    }
    return -1;
}

static int find_free_slot(void)
{
    for (uint8_t i = 0; i < MAX_KEYS; i++) {
        KeyRec k;
        eeprom_read_block(&k, &ee_keys[i], sizeof(KeyRec));
        if (k.used != 0xAA) return i;
    }
    return -1;
}

/* ==================== 7-сегментный индикатор ====================
   4 разряда, общий катод, динамическая индикация.
   PORTC[0..7] — сегменты a..g + dp;
   PORTA[0..3] — выбор разряда (активный низкий).                    */

static const uint8_t SEG[] = {
    /* 0     1     2     3     4     5     6     7     8     9   */
    0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
    /* E     d     S     C     blank */
    0x79, 0x5E, 0x6D, 0x39, 0x00
};
#define SEG_E   10
#define SEG_D   11
#define SEG_S   12
#define SEG_C   13
#define SEG_DP  0x80

static volatile uint8_t disp_mode = 0;   /* 0=E, 1=d, 2=S, 3=C */

static void display_init(void)
{
    DDRC  = 0xFF;         /* PORTC — сегменты (выход)  */
    DDRA |= 0x0F;         /* PORTA[0..3] — разряды     */
    PORTA |= 0x0F;        /* все разряды погашены      */
}

static void display_show(uint8_t letter_seg, uint16_t value)
{
    uint8_t digits[3] = {
        (value / 100) % 10,
        (value / 10)  % 10,
         value        % 10
    };
    /* Разряд 0: буква + десятичная точка */
    PORTC = SEG[letter_seg] | SEG_DP;
    PORTA = (PORTA & 0xF0) | 0x0E;
    delay_2ms_asm();
    /* Разряды 1..3: цифры */
    for (uint8_t i = 0; i < 3; i++) {
        PORTC = SEG[digits[i]];
        /* Активный низкий на PA[i+1]; маска только в младших 4 битах. */
        PORTA = (PORTA & 0xF0) | (0x0F ^ (0x01 << (i + 1)));
        delay_2ms_asm();
    }
    PORTA |= 0x0F;
}

/* ==================== Внешнее прерывание INT0 ==================== */
ISR(INT0_vect)
{
    disp_mode = (disp_mode + 1) & 0x03;
}

static void int0_init(void)
{
    DDRD  &= ~(1 << PD2);       /* PD2 — вход           */
    PORTD |=  (1 << PD2);       /* внутренняя подтяжка  */
    MCUCR |=  (1 << ISC01);     /* по падающему фронту  */
    MCUCR &= ~(1 << ISC00);
    GICR  |=  (1 << INT0);      /* разрешить INT0        */
}

/* ==================== Диспетчер команд ==================== */
static void dispatch(void)
{
    uint8_t cmd = uart_get();
    Stats st;
    eeprom_read_block(&st, &ee_stats, sizeof(Stats));

    switch (cmd) {

    case CMD_ADD_KEY: {
        uint16_t n = uart_get16();
        uint16_t e = uart_get16();
        uint16_t d = uart_get16();
        int slot = find_free_slot();
        if (slot < 0) { uart_put(ST_FULL); return; }
        KeyRec k = { n, e, d, 0xAA };
        eeprom_update_block(&k, &ee_keys[slot], sizeof(KeyRec));
        uart_put(ST_OK);
        uart_put((uint8_t)slot);
        return;
    }

    case CMD_DEL_KEY: {
        uint8_t slot = uart_get();
        if (slot >= MAX_KEYS) { uart_put(ST_BAD_PARAM); return; }
        KeyRec empty = {0, 0, 0, 0x00};
        eeprom_update_block(&empty, &ee_keys[slot], sizeof(KeyRec));
        uart_put(ST_OK);
        return;
    }

    case CMD_LIST_KEYS: {
        uart_put(ST_OK);
        uint8_t cnt = 0;
        for (uint8_t i = 0; i < MAX_KEYS; i++) {
            KeyRec k;
            eeprom_read_block(&k, &ee_keys[i], sizeof(KeyRec));
            if (k.used == 0xAA) cnt++;
        }
        uart_put(cnt);
        for (uint8_t i = 0; i < MAX_KEYS; i++) {
            KeyRec k;
            eeprom_read_block(&k, &ee_keys[i], sizeof(KeyRec));
            if (k.used == 0xAA) {
                uart_put16(k.n);
                uart_put16(k.e);
            }
        }
        return;
    }

    case CMD_ENCRYPT: {
        uint16_t n   = uart_get16();
        uint16_t e   = uart_get16();
        uint16_t len = uart_get16();
        uart_put(ST_OK);
        for (uint16_t i = 0; i < len; i++) {
            uint8_t  m = uart_get();
            uint16_t c = rsa_modexp((uint16_t)m, e, n);
            uart_put16(c);
        }
        st.enc_len += len;
        eeprom_update_block(&st, &ee_stats, sizeof(Stats));
        return;
    }

    case CMD_DECRYPT: {
        uint16_t n   = uart_get16();
        uint16_t e   = uart_get16();
        uint16_t len = uart_get16();
        KeyRec k;
        if (find_key(n, e, &k) < 0) {
            uart_put(ST_NO_KEY);
            return;
        }
        uart_put(ST_OK);
        for (uint16_t i = 0; i < len; i++) {
            uint16_t c = uart_get16();
            uint16_t m = rsa_modexp(c, k.d, k.n);
            uart_put((uint8_t)(m & 0xFF));
        }
        st.dec_len += len;
        eeprom_update_block(&st, &ee_stats, sizeof(Stats));
        return;
    }

    case CMD_SIGN: {
        uint16_t n    = uart_get16();
        uint16_t e    = uart_get16();
        uint16_t hash = uart_get16();
        KeyRec k;
        if (find_key(n, e, &k) < 0) { uart_put(ST_NO_KEY);    return; }
        if (hash >= n)              { uart_put(ST_BAD_PARAM); return; }
        uint16_t s = rsa_modexp(hash, k.d, k.n);
        uart_put(ST_OK);
        uart_put16(s);
        st.sign_cnt++;
        eeprom_update_block(&st, &ee_stats, sizeof(Stats));
        return;
    }

    case CMD_VERIFY: {
        uint16_t n    = uart_get16();
        uint16_t e    = uart_get16();
        uint16_t hash = uart_get16();
        uint16_t sig  = uart_get16();
        uint16_t m    = rsa_modexp(sig, e, n);
        uart_put(ST_OK);
        uart_put(m == hash ? 1 : 0);
        st.check_cnt++;
        eeprom_update_block(&st, &ee_stats, sizeof(Stats));
        return;
    }

    case CMD_GET_STATS: {
        uart_put(ST_OK);
        uart_put((uint8_t)(st.enc_len >> 24));
        uart_put((uint8_t)(st.enc_len >> 16));
        uart_put((uint8_t)(st.enc_len >>  8));
        uart_put((uint8_t) st.enc_len);
        uart_put((uint8_t)(st.dec_len >> 24));
        uart_put((uint8_t)(st.dec_len >> 16));
        uart_put((uint8_t)(st.dec_len >>  8));
        uart_put((uint8_t) st.dec_len);
        uart_put16(st.sign_cnt);
        uart_put16(st.check_cnt);
        return;
    }

    case CMD_RESET_STATS: {
        Stats zero = {0, 0, 0, 0};
        eeprom_update_block(&zero, &ee_stats, sizeof(Stats));
        uart_put(ST_OK);
        return;
    }

    default:
        uart_put(ST_INVALID_CMD);
        return;
    }
}

/* ==================== main ==================== */
int main(void)
{
    uart_init();
    display_init();
    int0_init();
    sei();

    for (;;) {
        /* Неблокирующая проверка UART: если пришёл байт — обработать команду. */
        if (UCSRA & (1 << RXC)) {
            dispatch();
        }
        /* Динамическая индикация (мультиплексирование разрядов). */
        Stats s;
        eeprom_read_block(&s, &ee_stats, sizeof(Stats));
        uint8_t  lt;
        uint16_t v;
        switch (disp_mode) {
            case 0: lt = SEG_E; v = (uint16_t)(s.enc_len   % 1000); break;
            case 1: lt = SEG_D; v = (uint16_t)(s.dec_len   % 1000); break;
            case 2: lt = SEG_S; v = s.sign_cnt   % 1000;            break;
            default:lt = SEG_C; v = s.check_cnt  % 1000;            break;
        }
        display_show(lt, v);
    }
}
