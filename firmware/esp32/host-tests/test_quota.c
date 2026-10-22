#include "quota.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <time.h>
static const int64_t NOW=1792634400; // 2026-10-22 02:00 UTC
static const char *head="{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"real\",\"providers\":[{\"provider\":\"codex\",\"status\":\"ok\",\"source\":\"codex-app-server\",\"stale\":false,\"collected_at\":\"2026-10-22T02:00:00Z\",\"windows\":[";
static const char *short_window="{\"name\":\"codex/primary\",\"used_percent\":31,\"remaining_percent\":69,\"duration_minutes\":300,\"resets_at\":\"2026-10-22T04:00:00Z\"}";
static const char *long_window="{\"name\":\"codex/secondary\",\"used_percent\":100,\"remaining_percent\":0,\"duration_minutes\":10080,\"resets_at\":\"2026-10-29T04:00:00Z\"}";
static bool parse_windows(const char *windows,quota_view *view){char json[2048];snprintf(json,sizeof(json),"%s%s]}]}",head,windows);return quota_parse(json,strlen(json),NOW,view);}
int main(void){
 setenv("TZ","UTC0",1);tzset();quota_view v={0};char windows[1024];snprintf(windows,sizeof(windows),"%s,%s",short_window,long_window);
 assert(parse_windows(windows,&v));assert(v.primary.known&&v.primary.remaining==69&&v.weekly.known&&v.weekly.remaining==0);assert(!v.stale);assert(v.collected_at==NOW);assert(!quota_expired(&v,NOW+599));assert(quota_expired(&v,NOW+601));
 assert(parse_windows(long_window,&v));assert(!v.primary.known&&v.weekly.known); // Policy projection must not relabel weekly as short.
 assert(parse_windows("",&v));assert(!v.primary.known&&!v.weekly.known);
 const char *empty="{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"real\",\"providers\":[]}";assert(quota_parse(empty,strlen(empty),NOW,&v)&&v.stale&&!v.primary.known);
 const char *bad[]={"{}","[]","{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"demo\",\"providers\":[]}","{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"real\",\"providers\":[]}trailing"};for(size_t i=0;i<sizeof(bad)/sizeof(*bad);i++)assert(!quota_parse(bad[i],strlen(bad[i]),NOW,&v));
 assert(!parse_windows("{\"name\":\"primary\",\"used_percent\":31,\"remaining_percent\":99}",&v));
 assert(!parse_windows("{\"name\":\"primary\",\"used_percent\":-1,\"remaining_percent\":101}",&v));
 char payload[2048];snprintf(payload,sizeof(payload),"%s%s]}]}",head,short_window);
 for(size_t n=0;n<strlen(payload);n++)assert(!quota_parse(payload,n,NOW,&v));
 const char *legacy="{\"schema_version\":1,\"device_id\":null,\"mode\":\"real\",\"providers\":[]}";assert(!quota_parse(legacy,strlen(legacy),NOW,&v));
 char *time=strstr(payload,"2026-10-22T02:00:00Z");assert(time);memcpy(time,"2026-10-22T09:00:00Z",20);assert(quota_parse(payload,strlen(payload),NOW,&v)&&v.stale);
 snprintf(payload,sizeof(payload),"%s%s]}]}",head,short_window);char *p=strstr(payload,"\"stale\":false");memcpy(p+8,"true ",5);assert(quota_parse(payload,strlen(payload),NOW,&v)&&v.stale);
 // Fractional/offset collection timestamps must describe the same UTC instant.
 const char *offset="{\"schema_version\":1,\"device_id\":\"aaaaaaaaaaaaaaaaaaaaaaaa\",\"mode\":\"real\",\"providers\":[{\"provider\":\"codex\",\"status\":\"ok\",\"source\":\"codex-app-server\",\"stale\":false,\"collected_at\":\"2026-10-22T10:00:00.123456+08:00\",\"windows\":[]}]}";
 assert(quota_parse(offset,strlen(offset),NOW,&v)&&v.collected_at==NOW&&!v.stale);
 puts("PASS: quotas, zero vs missing, restrictive weekly projection, malformed/truncated payloads, collection time/offset, future and offline expiry");
}
