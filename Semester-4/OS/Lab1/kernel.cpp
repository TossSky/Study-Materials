// Первая инструкция — jmp на kmain. Обязательно первой,
// т.к. загрузчик передаёт управление на начало бинарного образа.
__asm("jmp kmain");

#define VIDEO_BUF_PTR (0xb8000)
#define SCREEN_WIDTH 80

// Вывод строки в видеопамять
void out_str(int color, const char* ptr, unsigned int strnum)
{
    unsigned char* video_buf = (unsigned char*) VIDEO_BUF_PTR;
    video_buf += SCREEN_WIDTH * 2 * strnum;

    while (*ptr)
    {
        video_buf[0] = (unsigned char) *ptr;
        video_buf[1] = color;
        video_buf += 2;
        ptr++;
    }
}

// Очистка экрана (заполнение видеопамяти пробелами)
void clear_screen()
{
    unsigned char* video_buf = (unsigned char*) VIDEO_BUF_PTR;
    for (int i = 0; i < SCREEN_WIDTH * 25 * 2; i += 2)
    {
        video_buf[i] = ' ';
        video_buf[i + 1] = 0x07;
    }
}

extern "C" int kmain()
{
    clear_screen();
    out_str(0x07, "Welcome to ConvertOS!", 0);

    while(1)
    {
        asm("hlt");
    }

    return 0;
}
