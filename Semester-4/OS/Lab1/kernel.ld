SECTIONS {
    . = 0x10000;
    .text : {
        *(.text)
        *(.rodata*)
        *(.data)
        *(.bss)
    }
    /DISCARD/ : {
        *(.note*)
        *(.eh_frame*)
        *(.comment)
        *(.gnu*)
    }
}
