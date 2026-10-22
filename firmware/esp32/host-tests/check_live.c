#include "quota.h"
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
int main(void){
 setenv("TZ","UTC0",1);tzset();char payload[16385];size_t n=fread(payload,1,sizeof(payload),stdin);quota_view v;
 if(!quota_parse(payload,n,time(NULL),&v))return 1;
 printf("{\"primary_known\":%s,\"weekly_known\":%s,\"primary\":%.9f,\"weekly\":%.9f,\"stale\":%s}\n",v.primary.known?"true":"false",v.weekly.known?"true":"false",v.primary.remaining,v.weekly.remaining,v.stale?"true":"false");return 0;
}
