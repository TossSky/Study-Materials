#ifndef RSA_H
#define RSA_H

#include <stdint.h>

/* Модульное возведение в степень: base^exp mod m.
   m < 65536, поэтому промежуточные произведения держим в uint32_t. */
uint16_t rsa_modexp(uint16_t base, uint16_t exp, uint16_t m);

/* CRC-16-CCITT (poly 0x1021, init 0xFFFF) — используется как «хэш» сообщения
   перед подписанием. Значение редуцируется по модулю n вызывающим кодом. */
uint16_t crc16_ccitt(const uint8_t *data, uint32_t len);

#endif
