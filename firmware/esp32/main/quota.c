#include "quota.h"
#include "cJSON.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
// ISO8601 with mandatory UTC offset; server currently emits +00:00 / Z.
static int64_t timestamp(const char *s){
    if(!s)return 0;
    int y,m,d,h,n,sec,used=0;
    if(sscanf(s,"%4d-%2d-%2dT%2d:%2d:%2d%n",&y,&m,&d,&h,&n,&sec,&used)!=6)return 0;
    if(y<2020||y>2100||m<1||m>12||d<1||d>31||h<0||h>23||n<0||n>59||sec<0||sec>59)return 0;
    const char *p=s+used;if(*p=='.'){p++;if(*p<'0'||*p>'9')return 0;while(*p>='0'&&*p<='9')p++;}
    int offset=0;
    if(strcmp(p,"Z")!=0){int zh,zm,length=0;if((*p!='+'&&*p!='-')||sscanf(p+1,"%2d:%2d%n",&zh,&zm,&length)!=2||p[1+length]||zh<0||zh>23||zm<0||zm>59)return 0;offset=(zh*60+zm)*60*(*p=='+'?1:-1);}
    struct tm t={.tm_year=y-1900,.tm_mon=m-1,.tm_mday=d,.tm_hour=h,.tm_min=n,.tm_sec=sec};
    int64_t epoch=(int64_t)mktime(&t); // App fixes TZ=UTC before parsing.
    if(t.tm_year!=y-1900||t.tm_mon!=m-1||t.tm_mday!=d)return 0;
    return epoch-offset;
}
static double number(const cJSON *o,const char *key){const cJSON *v=cJSON_GetObjectItemCaseSensitive(o,key);return cJSON_IsNumber(v)?v->valuedouble:NAN;}
static const char *string(const cJSON *o,const char *key){return cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(o,key));}
bool quota_expired(const quota_view *v,int64_t epoch){
    return v->stale||epoch<1700000000||!v->collected_at||epoch-v->collected_at>600||v->collected_at>epoch+60||
        (v->primary.known&&v->primary.resets_at&&epoch>=v->primary.resets_at)||
        (v->weekly.known&&v->weekly.resets_at&&epoch>=v->weekly.resets_at);
}
bool quota_parse(const char *json,size_t length,int64_t epoch,quota_view *out){
    if(!json||!out||!length||length>16384||memchr(json,0,length))return false;
    const char *end=NULL;cJSON *root=cJSON_ParseWithLengthOpts(json,length,&end,false);if(!root)return false;
    quota_view v={.stale=true};bool ok=false;
    while(end<json+length&&(*end==' '||*end=='\n'||*end=='\r'||*end=='\t'))end++;
    if(end!=json+length||number(root,"schema_version")!=1)goto done;
    const char *mode=string(root,"mode");if(!mode||strcmp(mode,"real"))goto done;
    const cJSON *items=cJSON_GetObjectItemCaseSensitive(root,"providers");if(!cJSON_IsArray(items))goto done;
    const cJSON *item=NULL;int codex_count=0;
    cJSON_ArrayForEach(item,items){
        const char *provider=string(item,"provider");if(!provider||strcmp(provider,"codex"))continue;
        if(++codex_count>1)goto done;
        const char *source=string(item,"source"),*status=string(item,"status");
        v.collected_at=timestamp(string(item,"collected_at"));
        const cJSON *stale=cJSON_GetObjectItemCaseSensitive(item,"stale");
        if(!source||strcmp(source,"codex-app-server")||!status||strcmp(status,"ok")||!cJSON_IsBool(stale))continue;
        v.stale=cJSON_IsTrue(stale);
        const cJSON *windows=cJSON_GetObjectItemCaseSensitive(item,"windows"),*w=NULL;if(!cJSON_IsArray(windows)||cJSON_GetArraySize(windows)>32)goto done;
        cJSON_ArrayForEach(w,windows){
            const char *name=string(w,"name");double used=number(w,"used_percent"),remaining=number(w,"remaining_percent"),minutes=number(w,"duration_minutes");
            if(!name||!isfinite(used)||used<0||used>100||!isfinite(remaining)||remaining<0||remaining>100||fabs(remaining-(100-used))>0.001)goto done;
            bool weekly=(isfinite(minutes)&&minutes>=1440)||strstr(name,"secondary")||strstr(name,"weekly");
            quota_window *slot=weekly?&v.weekly:&v.primary;
            if(slot->known)continue; // Same first-slot semantics as the web display.
            slot->known=true;slot->remaining=remaining;slot->resets_at=timestamp(string(w,"resets_at"));
        }
    }
    v.stale=quota_expired(&v,epoch);*out=v;ok=true;
done:cJSON_Delete(root);return ok;
}
