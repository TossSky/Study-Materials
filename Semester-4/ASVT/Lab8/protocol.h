#ifndef PROTOCOL_H
#define PROTOCOL_H

/* ---------- Коды команд (ПК -> МК) ---------- */
#define CMD_ADD_KEY     0x01  /* payload: n(2) e(2) d(2)               */
#define CMD_DEL_KEY     0x02  /* payload: slot(1)                      */
#define CMD_LIST_KEYS   0x03  /* payload: —                            */
#define CMD_ENCRYPT     0x04  /* header:  n(2) e(2) len(2)  + stream   */
#define CMD_DECRYPT     0x05  /* header:  n(2) e(2) len(2)  + stream   */
#define CMD_SIGN        0x06  /* payload: n(2) e(2) hash(2)            */
#define CMD_VERIFY      0x07  /* payload: n(2) e(2) hash(2) sig(2)     */
#define CMD_GET_STATS   0x08  /* payload: —                            */
#define CMD_RESET_STATS 0x09  /* payload: —                            */

/* ---------- Коды статуса (МК -> ПК) ---------- */
#define ST_OK            0x00
#define ST_NO_KEY        0xE1  /* секретный ключ d не найден по (n,e)  */
#define ST_BAD_PARAM     0xE2  /* напр. m >= n, slot вне диапазона     */
#define ST_FULL          0xE3  /* EEPROM забит                         */
#define ST_INVALID_CMD   0xEF

/* Лимит хранилища */
#define MAX_KEYS 4

/* Многобайтовые поля в протоколе — big-endian. */

#endif
