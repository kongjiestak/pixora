#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct { bool known; double remaining; int64_t resets_at; } quota_window;
typedef struct { bool present,known; double temperature; int code; int64_t expires_at; char city[64]; } screen_weather;
typedef struct { screen_weather weather; bool stale; int64_t collected_at; quota_window primary,weekly; } quota_view;
bool quota_parse(const char *json, size_t length, int64_t epoch, quota_view *out);
bool quota_expired(const quota_view *view, int64_t epoch);

bool screen_weather_parse(const char *json,size_t length,int64_t epoch,screen_weather *out);
