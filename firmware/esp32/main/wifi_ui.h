#pragma once
#include <stdbool.h>
#define WIFI_UI_SCAN 1
#define WIFI_UI_CONNECT 2
#define WIFI_UI_LIMIT 12
typedef struct {char ssid[33];int rssi;bool secure,supported;} wifi_ui_network;
typedef struct {int kind;char ssid[33],password[65];bool secure;} wifi_ui_command;
