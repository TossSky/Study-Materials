;============================================================
; Лабораторная работа 2 — Вариант 6а
; Организация цифрового ввода-вывода (ATmega32, F_CPU = 8 МГц)
; -----------------------------------------------------------
; «Бегущий огонь» из 16 светодиодов на портах PORTA + PORTB.
; Базовый образ — конкатенация числа y и -y в ПРЯМОМ коде
; (старший байт — y, младший — -y; биты [15:8] идут на PORTB,
; биты  [7:0] — на PORTA).
;
; Параметры:
;   y      — пользовательское восьмиразрядное число (PORTC при PD7);
;   x      — шаг сдвига позиции, signed [−3 .. +3];
;   z      — индекс задержки {0,25 c; 0,5 c; 1 c};
;   PORTD: PD0,PD1 — индекс z; PD4,PD5 — |x|; PD6 — знак x.
;
; Внешние прерывания (по падающему фронту):
;   INT0 (PD2) → x ← x+1; если x > 3, то x ← −3.
;   INT1 (PD3) → z ← (z + 1) mod 3.
; Изменения сохраняются во внутреннем EEPROM.
;
; При запуске значения x и z считываются из EEPROM. «Свежий» чип
; распознаётся по магической метке EE_MAGIC по адресу EE_MAGIC_ADDR;
; в этом случае инициализация выполняется значениями по умолчанию
; (x = 1, z = 0) и метка записывается.
;============================================================

.include "m32def.inc"

; ----- распределение регистров -----
.def TMP    = R16        ; рабочий
.def TMP2   = R17        ; рабочий 2
.def Y_VAL  = R18        ; пользовательское y
.def NY_VAL = R19        ; -y в прямом коде (старший бит y инвертирован)
.def POS    = R20        ; позиция «бегущего огня», 0..15
.def X_VAL  = R21        ; шаг x  (signed: −3..+3, хранится в two's complement)
.def Z_IDX  = R22        ; индекс задержки 0..2
.def FLAGS  = R23        ; флаги ожидающих записей в EEPROM

.equ FLG_SAVE_X = 0
.equ FLG_SAVE_Z = 1

; ----- адреса в EEPROM -----
.equ EE_X_ADDR     = 0x0000
.equ EE_Z_ADDR     = 0x0001
.equ EE_MAGIC_ADDR = 0x0002
.equ EE_MAGIC      = 0xA5

;============================================================
;                Таблица векторов прерываний
;============================================================
.cseg
.org 0x0000
    rjmp reset                ; Reset
.org INT0addr
    rjmp ext_int0             ; INT0 — кнопка PD2
.org INT1addr
    rjmp ext_int1             ; INT1 — кнопка PD3

;============================================================
;        Базовая задержка ~ 250 мс (8 МГц → ~2 000 000 тактов)
;
; Структура — два вложенных счётчика по 256 итераций и
; внешний счётчик 10 повторений:
;   N ≈ 10 · 256 · 256 · 3 = 1 966 080 такта ≈ 246 мс.
; Допустимая для бегущего огня погрешность.
;============================================================
.org 0x0040
delay_250ms:
    push R24
    push R25
    push R26
    ldi  R24, 10
d250_o:
    ldi  R25, 0
d250_m:
    ldi  R26, 0
d250_i:
    dec  R26
    brne d250_i
    dec  R25
    brne d250_m
    dec  R24
    brne d250_o
    pop  R26
    pop  R25
    pop  R24
    ret

; Задержка z в зависимости от Z_IDX: 1×, 2× или 4× по 250 мс
delay_z:
    cpi  Z_IDX, 0
    brne dz_check1
    rcall delay_250ms
    ret
dz_check1:
    cpi  Z_IDX, 1
    brne dz_check2
    rcall delay_250ms
    rcall delay_250ms
    ret
dz_check2:
    rcall delay_250ms
    rcall delay_250ms
    rcall delay_250ms
    rcall delay_250ms
    ret

; Задержка ~120 мс — антидребезг при вводе y с PORTC
delay_120ms:
    push R24
    push R25
    push R26
    ldi  R24, 5
d120_o: ldi R25, 0
d120_m: ldi R26, 0
d120_i: dec R26
        brne d120_i
        dec R25
        brne d120_m
        dec R24
        brne d120_o
    pop  R26
    pop  R25
    pop  R24
    ret

;============================================================
;                       EEPROM
;============================================================
ee_wait:
    sbic EECR, EEWE
    rjmp ee_wait
    ret

ee_read_byte:                  ; вход: TMP2 — адрес; выход: TMP — значение
    rcall ee_wait
    clr   TMP
    out   EEARH, TMP
    out   EEARL, TMP2
    sbi   EECR, EERE
    in    TMP, EEDR
    ret

ee_write_byte:                 ; вход: TMP2 — адрес, TMP — значение
    rcall ee_wait
    push  TMP
    clr   TMP
    out   EEARH, TMP
    out   EEARL, TMP2
    pop   TMP
    out   EEDR, TMP
    cli
    sbi   EECR, EEMWE
    sbi   EECR, EEWE
    sei
    ret

ee_save_x:
    mov   TMP,  X_VAL
    ldi   TMP2, EE_X_ADDR
    rcall ee_write_byte
    ret

ee_save_z:
    mov   TMP,  Z_IDX
    ldi   TMP2, EE_Z_ADDR
    rcall ee_write_byte
    ret

;============================================================
;                Обработчики прерываний
;============================================================

; INT0 (PD2): x ← x + 1; если x > 3, то x ← −3
ext_int0:
    push TMP
    in   TMP, SREG
    push TMP

    inc  X_VAL
    mov  TMP, X_VAL
    cpi  TMP, 4
    brne i0_done
    ldi  X_VAL, -3
i0_done:
    sbr  FLAGS, (1<<FLG_SAVE_X)

    pop  TMP
    out  SREG, TMP
    pop  TMP
    reti

; INT1 (PD3): z ← (z + 1) mod 3
ext_int1:
    push TMP
    in   TMP, SREG
    push TMP

    inc  Z_IDX
    cpi  Z_IDX, 3
    brlo i1_done
    clr  Z_IDX
i1_done:
    sbr  FLAGS, (1<<FLG_SAVE_Z)

    pop  TMP
    out  SREG, TMP
    pop  TMP
    reti

;============================================================
;                Вспомогательные подпрограммы
;============================================================

; Пересчитать NY_VAL = −y в прямом коде (только знаковый бит).
update_neg:
    mov  NY_VAL, Y_VAL
    ldi  TMP, 0x80
    eor  NY_VAL, TMP
    ret

; Сформировать в TMP2:TMP циклически сдвинутый влево на POS бит
; 16-битный образ (NY_VAL — младший байт, Y_VAL — старший).
build_pattern:
    mov  TMP,  NY_VAL          ; младший байт → PORTA
    mov  TMP2, Y_VAL           ; старший байт → PORTB
    push R24
    mov  R24, POS
    cpi  R24, 0
    breq bp_done
bp_loop:
    lsl  TMP                   ; C ← старший бит TMP
    rol  TMP2                  ; C → младший бит TMP2;
                               ; новый C = выпавший старший бит TMP2
    brcc bp_no_carry
    ori  TMP, 0x01             ; вернуть в младший разряд TMP
bp_no_carry:
    dec  R24
    brne bp_loop
bp_done:
    pop  R24
    ret

; Состояние PORTD:
;   PD0..PD1 — Z_IDX (2 бита);
;   PD4..PD5 — |x|   (2 бита);
;   PD6      — знак x (1 = отрицательное);
;   PD2,PD3,PD7 — pull-up (входы кнопок).
update_portd:
    push TMP2
    ldi  TMP, 0x8C             ; pull-up на PD2, PD3, PD7

    mov  TMP2, Z_IDX
    andi TMP2, 0x03
    or   TMP, TMP2

    mov  TMP2, X_VAL
    sbrc TMP2, 7
    neg  TMP2
    andi TMP2, 0x03
    swap TMP2                  ; младшие 4 бита → старшие
    andi TMP2, 0x30
    or   TMP, TMP2

    sbrc X_VAL, 7
    ori  TMP, 0x40

    out  PORTD, TMP
    pop  TMP2
    ret

; Считать y с PORTC при удержании PD7.
;   PORTC настроен как вход с pull-up; нажатие → 0 на пине, y = ~PINC.
read_y:
ry_wait_press:
    sbic PIND, 7               ; PD7 отжата → выходим, не меняя y
    rjmp ry_exit
    in   TMP, PINC
    com  TMP                   ; инвертируем (active-low)
    cpi  TMP, 0
    breq ry_wait_press         ; ни одной кнопки не нажато — ждём

    rcall delay_120ms          ; даём оператору дозажать остальные

    sbic PIND, 7
    rjmp ry_exit
    in   Y_VAL, PINC
    com  Y_VAL
    rcall update_neg

ry_wait_release:
    sbic PIND, 7               ; PD7 отжата → конец ввода
    rjmp ry_exit
    in   TMP, PINC
    com  TMP
    cpi  TMP, 0
    brne ry_wait_release       ; ждём пока все кнопки отпустят
ry_exit:
    ret

; Сохранить отложенные изменения в EEPROM (вызывается в основном цикле).
flush_flags:
    sbrs FLAGS, FLG_SAVE_X
    rjmp ff_check_z
    rcall ee_save_x
    cbr  FLAGS, (1<<FLG_SAVE_X)
ff_check_z:
    sbrs FLAGS, FLG_SAVE_Z
    rjmp ff_done
    rcall ee_save_z
    cbr  FLAGS, (1<<FLG_SAVE_Z)
ff_done:
    ret

;============================================================
;                       Точка входа
;============================================================
reset:
    ; --- стек ---
    ldi  TMP, high(RAMEND)
    out  SPH, TMP
    ldi  TMP, low(RAMEND)
    out  SPL, TMP

    ; --- порты ввода/вывода ---
    ldi  TMP, 0xFF
    out  DDRA, TMP             ; PORTA — выход
    out  DDRB, TMP             ; PORTB — выход
    clr  TMP
    out  DDRC, TMP             ; PORTC — вход
    ldi  TMP, 0xFF
    out  PORTC, TMP            ; pull-up на всех PORTC
    ldi  TMP, 0x73             ; PD0,1,4,5,6 — выход; PD2,3,7 — вход
    out  DDRD, TMP
    ldi  TMP, 0x8C             ; pull-up на PD2, PD3, PD7
    out  PORTD, TMP

    ; --- начальные значения ---
    clr  POS
    clr  FLAGS
    ldi  Y_VAL, 0x73           ; согласно варианту 6
    rcall update_neg

    ; --- проверка магической метки в EEPROM ---
    ldi  TMP2, EE_MAGIC_ADDR
    rcall ee_read_byte         ; → TMP
    cpi  TMP, EE_MAGIC
    breq ee_present

    ; «Свежий» чип: записать дефолты и метку
    ldi  X_VAL, 1
    clr  Z_IDX
    rcall ee_save_x
    rcall ee_save_z
    ldi  TMP, EE_MAGIC
    ldi  TMP2, EE_MAGIC_ADDR
    rcall ee_write_byte
    rjmp init_done

ee_present:
    ldi  TMP2, EE_X_ADDR
    rcall ee_read_byte
    mov  X_VAL, TMP

    ldi  TMP2, EE_Z_ADDR
    rcall ee_read_byte
    mov  Z_IDX, TMP
    cpi  Z_IDX, 3
    brlo init_done             ; Z_IDX в [0..2]
    clr  Z_IDX                 ; защита от мусора

init_done:
    ; --- внешние прерывания INT0, INT1 по падающему фронту ---
    ldi  TMP, (1<<ISC11)|(1<<ISC01)
    out  MCUCR, TMP
    ldi  TMP, (1<<INT0)|(1<<INT1)
    out  GICR, TMP
    out  GIFR, TMP             ; сбросить ждущие флаги

    sei                        ; разрешить общие прерывания

;============================================================
;                       Основной цикл
;============================================================
main_loop:
    rcall flush_flags          ; 1) записать ожидающие изменения в EEPROM

    sbis PIND, 7               ; 2) PD7 нажата? → режим ввода y
    rjmp pause_mode

    rcall build_pattern        ; 3) построить образ и вывести
    out   PORTA, TMP
    out   PORTB, TMP2

    rcall update_portd         ; 4) обновить индикацию режима

    rcall delay_z              ; 5) задержка z

    add   POS, X_VAL           ; 6) POS ← (POS + x) mod 16
    andi  POS, 0x0F

    rjmp  main_loop

pause_mode:
    rcall read_y
    rjmp  main_loop
