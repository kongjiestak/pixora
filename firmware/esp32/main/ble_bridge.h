#pragma once
#include "usb_protocol.h"
#include "esp_err.h"
esp_err_t ble_bridge_init(const char *scoped_token);
void ble_bridge_enable(bool enabled);
bool ble_bridge_receive(usb_message *message);
