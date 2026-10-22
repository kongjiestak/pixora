#include "quota.h"
#include "cJSON.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static const int64_t NOW=1792634400;
static cJSON *fixture(void){return cJSON_Parse("{\"schema_version\":2,\"observations\":[{\"provider\":\"weather\",\"mode\":\"real\",\"source\":\"open-meteo\",\"status\":\"ok\",\"collected_at\":\"2026-10-22T02:00:00Z\",\"expires_at\":\"2026-10-22T03:00:00Z\",\"entries\":[{\"title\":\"Shanghai\"}],\"metrics\":[{\"key\":\"weather.temperature\",\"value\":0,\"unit\":\"celsius\"},{\"key\":\"weather.code\",\"value\":0,\"unit\":\"wmo-code\"},{\"key\":\"weather.model_time\",\"value\":1792634400,\"unit\":\"unix-seconds\"}]}]}");}
static screen_weather parse(cJSON *root,int64_t now){char *s=cJSON_PrintUnformatted(root);screen_weather w={0};assert(screen_weather_parse(s,strlen(s),now,&w));free(s);return w;}
int main(void){
 setenv("TZ","UTC0",1);tzset();cJSON *r=fixture();screen_weather w=parse(r,NOW);assert(w.known&&w.temperature==0&&w.code==0&&!strcmp(w.city,"Shanghai"));assert(!parse(r,NOW+3600).known);
 cJSON *o=cJSON_GetArrayItem(cJSON_GetObjectItem(r,"observations"),0);
 cJSON_ReplaceItemInObject(o,"mode",cJSON_CreateString("demo"));assert(!parse(r,NOW).known);cJSON_ReplaceItemInObject(o,"mode",cJSON_CreateString("real"));
 cJSON *temperature=cJSON_GetArrayItem(cJSON_GetObjectItem(o,"metrics"),0);cJSON_ReplaceItemInObject(temperature,"unit",cJSON_CreateString("fahrenheit"));assert(!parse(r,NOW).known);cJSON_ReplaceItemInObject(temperature,"unit",cJSON_CreateString("celsius"));
 cJSON_SetNumberValue(cJSON_GetObjectItem(temperature,"value"),999);assert(!parse(r,NOW).known);
 cJSON_Delete(r);r=cJSON_Parse("{\"schema_version\":2,\"observations\":[]}");assert(!parse(r,NOW).present);cJSON_Delete(r);
 assert(!screen_weather_parse("{}",2,NOW,&w));assert(!screen_weather_parse("{",1,NOW,&w));
 puts("PASS: real scoped weather, zero temperature/code, expiry, demo/unit/range rejection, missing authorization");
}
