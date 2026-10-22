#pragma once
#include "quota.h"
void screen_ui_create(void (*request_setup)(void));
void screen_ui_update(const quota_view *view,bool fetched,const char *state,int64_t received);
void screen_ui_pause(void);
