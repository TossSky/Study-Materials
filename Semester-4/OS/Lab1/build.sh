#!/bin/bash
set -e

yasm -f bin -o bootsect.bin bootsect.asm

g++ -ffreestanding -m32 -fno-pic -fno-exceptions -fno-rtti -o kernel.o -c kernel.cpp
ld --oformat binary -T kernel.ld -o kernel.bin --entry=kmain -m elf_i386 kernel.o

SIZE=$(wc -c < kernel.bin)
SECTORS=$(( (SIZE + 511) / 512 ))
echo "kernel.bin: $SIZE bytes ($SECTORS sectors)"
echo "Done. Run: qemu-system-i386 -fda bootsect.bin -fdb kernel.bin"
