[BITS 16]
[ORG 0x7c00]

start:
    ; === Инициализация сегментов ===
    mov ax, cs
    mov ds, ax
    mov ss, ax
    mov sp, start

    ; === Очистка экрана ===
    mov ax, 0x0003
    int 0x10
    xor ax, ax

    mov si, 0               ; Индекс текущего цвета (0,2,4,6,8,10)

; === Главный цикл: вывод названия цвета + ожидание клавиши ===
clo:
    mov bx, color_table
    add bx, si
    mov bx, [bx]            ; bx = адрес строки текущего цвета
    call print_str

    mov ah, 0x00
    int 0x16                 ; Ожидание нажатия клавиши (ah = скан-код)

    cmp ah, 0x48             ; Стрелка вверх
    je go_up
    cmp ah, 0x50             ; Стрелка вниз
    je go_down
    jmp redraw               ; Любая другая клавиша — перерисовка

go_up:
    sub si, 2
    jns redraw
    mov si, 10               ; Wrap: 0 -> последний
    jmp redraw

go_down:
    add si, 2
    cmp si, 12
    jl redraw
    mov si, 0                ; Wrap: последний -> 0

redraw:
    mov ax, 0x0003           ; Очистка экрана
    int 0x10
    xor ax, ax
    jmp clo

; === Загрузка ядра с диска (int 0x13, ah=0x02) ===
; Ядро лежит на втором диске (-fdb kernel.bin), читаем в 0x1000:0x0000 = 0x10000
load_kernel:
    mov ah, 0x02
    mov al, 1                ; Количество секторов (поменяй под размер kernel.bin)
    mov ch, 0
    mov cl, 1
    mov dh, 0
    mov dl, 1                ; Диск 1 (второй диск, -fdb)
    mov bx, 0x1000
    mov es, bx
    xor bx, bx
    int 0x13

    ; === Переключение в защищённый режим ===
    cli
    lgdt [gdt_info]

    in al, 0x92              ; Включение A20
    or al, 2
    out 0x92, al

    mov eax, cr0             ; Установка бита PE
    or al, 1
    mov cr0, eax

    jmp 0x8:protected_mode   ; Дальний переход в 32-бит


; === Данные ===
color_table:
    dw color_0, color_1, color_2, color_3, color_4, color_5

color_codes:
    db 0x07, 0x0F, 0x0E, 0x01, 0x04, 0x02

color_0: db "gray", 0
color_1: db "white", 0
color_2: db "yellow", 0
color_3: db "blue", 0
color_4: db "red", 0
color_5: db "green", 0


; === Функция: вывод строки с цветом ===
; Вход: bx = адрес строки, si = индекс цвета (0,2,4,...,10)
print_str:
    mov di, bx
    push si
    shr si, 1
    mov dl, [color_codes + si]
    pop si
.loop:
    mov al, [di]
    test al, al
    jz .done
    push dx                  ; Сохраняем цвет
    mov ah, 0x09
    mov bl, dl
    mov bh, 0
    mov cx, 1
    int 0x10
    mov ah, 0x03             ; Получить позицию курсора
    mov bh, 0
    int 0x10
    inc dl                   ; Столбец + 1
    mov ah, 0x02             ; Установить позицию курсора
    int 0x10
    pop dx                   ; Восстанавливаем цвет
    inc di
    jmp .loop
.done:
    ret


[BITS 32]
protected_mode:
    mov ax, 0x10
    mov es, ax
    mov ds, ax
    mov ss, ax
    call 0x10000
    jmp $


; === GDT ===
gdt:
    db 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    db 0xff, 0xff, 0x00, 0x00, 0x00, 0x9A, 0xCF, 0x00
    db 0xff, 0xff, 0x00, 0x00, 0x00, 0x92, 0xCF, 0x00

gdt_info:
    dw gdt_info - gdt
    dw gdt, 0

    times (512 - ($ - start) - 2) db 0
    db 0x55, 0xAA
