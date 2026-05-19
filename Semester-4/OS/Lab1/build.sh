#!/bin/bash
# ConvertOS (вариант 15): YASM Intel + gcc, ОС Linux.
# Собирает bootsect.bin (загрузочный сектор, 512 байт) и kernel.bin (плоский 32-бит образ).
# Зависимости: yasm, gcc-multilib (g++ -m32 + ld -m elf_i386).
set -e

# --- Загрузчик: 16-битный real mode, YASM Intel ---
yasm -f bin -o bootsect.bin bootsect.asm

# --- Ядро: 32-битный freestanding C++ ---
g++ -m32 -c kernel.cpp -o kernel.o            \
    -ffreestanding -fno-pic -fno-pie          \
    -fno-exceptions -fno-rtti                 \
    -fno-builtin -fno-stack-protector         \
    -fno-asynchronous-unwind-tables           \
    -Wall -Wextra -O2

ld -m elf_i386 -nostdlib --oformat binary     \
   -T kernel.ld --entry=_start                \
   -o kernel.bin kernel.o

# --- Диагностика размеров ---
KSIZE=$(wc -c < kernel.bin)
KSECT=$(( (KSIZE + 511) / 512 ))
echo "bootsect.bin: $(wc -c < bootsect.bin) bytes"
echo "kernel.bin:   ${KSIZE} bytes (${KSECT} sectors)"
if [ "$KSECT" -gt 18 ]; then
    echo "WARN: kernel занимает ${KSECT} секторов, а загрузчик читает 18 за раз."
    echo "      Увеличь 'mov al, 18' и реализуй чтение в несколько вызовов int 0x13."
fi
echo
echo "Запуск в QEMU:"
echo "  qemu-system-i386 -fda bootsect.bin -fdb kernel.bin"
