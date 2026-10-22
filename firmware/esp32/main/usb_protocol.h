#pragma once
#include "quota.h"
#define USB_FRAME_MAX 20000
typedef struct {quota_view quota;int64_t epoch;uint32_t sequence;int kind;} usb_message;
// kind 1: signed data; 2: upstream authorization revoked; 3: upstream offline.
bool usb_digest(const char *key,const char *data,size_t size,char hex[65]);
bool usb_frame_parse(const char *frame,size_t length,const char *token,const char *nonce,usb_message *out);
