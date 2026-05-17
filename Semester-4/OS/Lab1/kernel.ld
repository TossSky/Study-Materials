/* ConvertOS flat-binary layout. Ядро грузится загрузчиком по адресу 0x10000.
   .text.entry должна идти первой — туда и прыгает загрузчик через call 0x10000. */
SECTIONS {
    . = 0x10000;
    .text : {
        *(.text.entry)
        *(.text*)
        *(.rodata*)
        *(.data*)
        *(.bss*)
        *(COMMON)
    }
    /DISCARD/ : {
        *(.note*)
        *(.eh_frame*)
        *(.comment)
        *(.gnu*)
    }
}
