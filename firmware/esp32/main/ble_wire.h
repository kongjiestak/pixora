#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define BLE_WIRE_MAX_PLAIN 20000
#define BLE_WIRE_HEADER 20
#define BLE_WIRE_TAG 16
#define BLE_WIRE_MAX (BLE_WIRE_HEADER+BLE_WIRE_MAX_PLAIN+BLE_WIRE_TAG)
typedef struct {
    uint8_t bytes[BLE_WIRE_MAX];
    size_t used,expected;
    bool failed;
} ble_wire_buffer;
void ble_wire_reset(ble_wire_buffer *buffer);
/* -1 rejected/poisoned; 0 more bytes needed; 1 complete. No heap allocation. */
int ble_wire_feed(ble_wire_buffer *buffer,const uint8_t *chunk,size_t size);
/* Decrypt only; caller must still validate signed frame/session/sequence. */
bool ble_wire_open(const ble_wire_buffer *buffer,const char *token,
                   uint8_t *plaintext,size_t capacity,size_t *written);
