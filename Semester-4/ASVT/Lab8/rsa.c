#include "rsa.h"

uint16_t rsa_modexp(uint16_t base, uint16_t exp, uint16_t m)
{
    if (m == 1) return 0;
    uint32_t result = 1;
    uint32_t b = base % m;
    while (exp > 0) {
        if (exp & 1) {
            result = (result * b) % m;
        }
        exp >>= 1;
        b = (b * b) % m;
    }
    return (uint16_t)result;
}

uint16_t crc16_ccitt(const uint8_t *data, uint32_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= ((uint16_t)data[i]) << 8;
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else              crc = (crc << 1);
        }
    }
    return crc;
}
