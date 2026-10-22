#include "usb_protocol.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
static const char *key="test-device-key-only-not-a-real-token";
static const char *nonce="0123456789abcdef0123456789abcdef";
static void make(const char *body,char *out,size_t capacity){
 char input[4096],signature[65];snprintf(input,sizeof(input),"data %s 1792634400 1\n%s",nonce,body);assert(usb_digest(key,input,strlen(input),signature));snprintf(out,capacity,"PXUSB1 %s 1792634400 1 %s %s",nonce,signature,body);
}
int main(void){
 setenv("TZ","UTC0",1);tzset();char digest[65];
 assert(usb_digest("Jefe","what do ya want for nothing?",28,digest));
 assert(!strcmp(digest,"5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"));
 char frame[4096];usb_message message;
 make("{\"event\":\"offline\"}",frame,sizeof(frame));assert(usb_frame_parse(frame,strlen(frame),key,nonce,&message)&&message.kind==3);
 assert(!usb_frame_parse(frame,strlen(frame),"wrong-device-key",nonce,&message));
 assert(!usb_frame_parse(frame,strlen(frame),key,"1123456789abcdef0123456789abcdef",&message));
 for(size_t n=0;n<strlen(frame);n++)assert(!usb_frame_parse(frame,n,key,nonce,&message));
 frame[strlen(frame)-2]^=1;assert(!usb_frame_parse(frame,strlen(frame),key,nonce,&message));
 make("{\"event\":\"revoked\"}",frame,sizeof(frame));assert(usb_frame_parse(frame,strlen(frame),key,nonce,&message)&&message.kind==2);
 make("{\"event\":\"offline\",\"extra\":true}",frame,sizeof(frame));assert(!usb_frame_parse(frame,strlen(frame),key,nonce,&message));
 make("{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"real\",\"providers\":[]}",frame,sizeof(frame));assert(usb_frame_parse(frame,strlen(frame),key,nonce,&message)&&message.kind==1&&message.quota.stale);
 make("{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"demo\",\"providers\":[]}",frame,sizeof(frame));assert(!usb_frame_parse(frame,strlen(frame),key,nonce,&message));
 assert(!usb_frame_parse(frame,USB_FRAME_MAX+1,key,nonce,&message));
 puts("USB HMAC RFC vector, device/boot binding, tamper, truncation, events and feed semantics passed");
}
