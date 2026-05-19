[BITS 16]
[ORG 0x7C00]

PARAM_ATTR equ 0x7E00           ; VGA-атрибут выбранного цвета (1 байт)
PARAM_IDX  equ 0x7E01           ; индекс цвета 0..5 (1 байт)
N_COLORS   equ 6

; ----- Точка входа: инициализация сегментов и стека --------------------------
start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti

    mov byte [cur_idx], 0       ; стартовый цвет — gray

; ----- Главный цикл: перерисовать экран и ждать клавишу ----------------------
main_loop:
    call clear_screen
    call draw_state
    call wait_key
    cmp ah, 0x48                ; стрелка вверх
    je  on_up
    cmp ah, 0x50                ; стрелка вниз
    je  on_down
    cmp ah, 0x1C                ; Enter
    je  load_kernel
    jmp main_loop

; ----- Реакция на «вверх»: индекс--, с заворотом 0->N-1 ----------------------
on_up:
    mov al, [cur_idx]
    cmp al, 0
    jne .dec
    mov al, N_COLORS - 1
    jmp .save
.dec:
    dec al
.save:
    mov [cur_idx], al
    jmp main_loop

; ----- Реакция на «вниз»: индекс++, с заворотом N-1->0 -----------------------
on_down:
    mov al, [cur_idx]
    inc al
    cmp al, N_COLORS
    jne .save
    xor al, al
.save:
    mov [cur_idx], al
    jmp main_loop

; ----- Установка видеорежима 80x25 текст (int 10h, ah=0, al=3) ---------------
clear_screen:
    mov ax, 0x0003
    int 0x10
    ret

; ----- Ожидание нажатия клавиши: BIOS int 0x16, ah=0 -------------------------
wait_key:
    xor ax, ax
    int 0x16
    ret

; ----- Установить курсор. DH=строка, DL=колонка (BH=страница 0) --------------
set_cursor:
    push ax
    push bx
    mov ah, 0x02
    mov bh, 0
    int 0x10
    pop bx
    pop ax
    ret

; ----- Печать 0-терминированной строки через teletype. SI=указатель ----------
teletype:
    push ax
    push bx
    push si
.loop:
    mov al, [si]
    test al, al
    jz  .done
    mov ah, 0x0E
    mov bh, 0
    int 0x10
    inc si
    jmp .loop
.done:
    pop si
    pop bx
    pop ax
    ret

; ----- Отрисовка интерфейса загрузчика: header + текущий цвет + подсказка ----
draw_state:
    pusha
    mov dh, 1                   ; (1,2) — заголовок
    mov dl, 2
    call set_cursor
    mov si, hdr_msg
    call teletype

    mov dh, 3                   ; (3,2) — лейбл "Color: "
    mov dl, 2
    call set_cursor
    mov si, label_msg
    call teletype

    movzx bx, byte [cur_idx]    ; имя текущего цвета по индексу
    shl bx, 1
    mov si, [color_names + bx]
    call teletype

    mov dh, 5                   ; (5,2) — подсказка
    mov dl, 2
    call set_cursor
    mov si, hint_msg
    call teletype
    popa
    ret

; ----- Сохранение параметров, загрузка ядра и переход в protected mode -------
load_kernel:
    movzx bx, byte [cur_idx]
    mov al, [color_attrs + bx]
    mov [PARAM_ATTR], al
    mov al, [cur_idx]
    mov [PARAM_IDX], al

    ; читаем 18 секторов (до конца дорожки) с fdb в 0x1000:0000
    mov ax, 0x1000
    mov es, ax
    xor bx, bx
    mov ah, 0x02                ; функция «прочитать секторы»
    mov al, 18                  ; кол-во секторов (1 дорожка)
    mov ch, 0                   ; цилиндр 0
    mov cl, 1                   ; начальный сектор 1
    mov dh, 0                   ; головка 0
    mov dl, 1                   ; диск 1 (fdb)
    int 0x13
    jc  disk_error

    cli
    lgdt [gdt_info]
    in   al, 0x92               ; включить адресную линию A20
    or   al, 2
    out  0x92, al
    mov  eax, cr0               ; PE := 1
    or   al, 1
    mov  cr0, eax
    jmp  0x8:protected_mode

; ----- Обработчик ошибки чтения диска: сообщить и зависнуть ------------------
disk_error:
    mov dh, 12
    mov dl, 2
    call set_cursor
    mov si, err_msg
    call teletype
.hang:
    hlt
    jmp .hang

; ----- Данные ----------------------------------------------------------------
hdr_msg:    db "ConvertOS bootloader.", 0
label_msg:  db "Color: ", 0
hint_msg:   db "Up/Down: change color, Enter: boot.", 0
err_msg:    db "Disk read error!", 0

cur_idx:    db 0

color_names:
    dw name_gray, name_white, name_yellow, name_blue, name_red, name_green
color_attrs:
    db 0x07, 0x0F, 0x0E, 0x09, 0x0C, 0x0A

name_gray:   db "gray",   0
name_white:  db "white",  0
name_yellow: db "yellow", 0
name_blue:   db "blue",   0
name_red:    db "red",    0
name_green:  db "green",  0

; ----- Глобальная таблица дескрипторов (null, code32, data32) ----------------
gdt:
    db 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    db 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x9A, 0xCF, 0x00
    db 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x92, 0xCF, 0x00
gdt_info:
    dw gdt_info - gdt - 1
    dd gdt

[BITS 32]
; ----- Первые инструкции в protected mode: настроить сегменты и прыгнуть -----
protected_mode:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov esp, 0x9FC00
    call 0x10000
.hang:
    hlt
    jmp .hang

    times (510 - ($ - $$)) db 0
    db 0x55, 0xAA
