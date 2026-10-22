#pragma once
#include "quota.h"
#include "wifi_ui.h"
void screen_ui_create(void (*request_setup)(void),bool (*request_wifi)(const wifi_ui_command *),void (*request_usb)(bool));
void screen_ui_wifi_scan_result(const wifi_ui_network *rows,unsigned count,const char *message);
void screen_ui_wifi_connect_result(bool ok,const char *message);
void screen_ui_update(const quota_view *view,bool fetched,const char *state,int64_t received,bool usb_source);
void screen_ui_pause(void);

void screen_ui_open_wifi(void);
