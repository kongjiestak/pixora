#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <stdatomic.h>
#include <assert.h>
#include <ctype.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_http_server.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "esp_sntp.h"
#include "lwip/sockets.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "lvgl.h"
#include "bsp/esp-bsp.h"
#include "cJSON.h"
#include "quota.h"
#include "screen_ui.h"
#include "wifi_credentials.h"
#include "setup_address.h"
#include "setup_request.h"

// Private configuration is provisioned in NVS, never built into the firmware.
static char ssid[33],password[65],server[257],token[129];
static EventGroupHandle_t network;
static QueueHandle_t wifi_commands;
static atomic_bool setup_active;
static lv_obj_t *screen;
static atomic_bool setup_requested;
static quota_view last;
static bool fetched;
static const char *state="CONNECTING";
static char ap_name[32],ap_pass[17],setup_nonce[33];
static int64_t last_received;
static void setup_start(void);
static bool config_valid(void){
    size_t n=strlen(token);
    if(strncmp(server,"https://",8)||strlen(server)<10||strlen(server)>240||n<32||n>128)return false;
    for(const char *p=server;*p;p++)if(isspace((unsigned char)*p)||*p=='@'||*p=='?'||*p=='#'||*p=='\\')return false;
    for(const char *p=token;*p;p++)if(!isalnum((unsigned char)*p)&&*p!='_'&&*p!='-')return false;
    return true;
}
static void load_config(void){
    nvs_handle_t h;if(nvs_open("pixora",NVS_READONLY,&h)!=ESP_OK)return;
    size_t n=sizeof(ssid);if(nvs_get_str(h,"ssid",ssid,&n)!=ESP_OK)ssid[0]=0;
    n=sizeof(password);if(nvs_get_str(h,"password",password,&n)!=ESP_OK)password[0]=0;
    n=sizeof(server);if(nvs_get_str(h,"server",server,&n)!=ESP_OK)server[0]=0;
    n=sizeof(token);if(nvs_get_str(h,"token",token,&n)!=ESP_OK)token[0]=0;
    wifi_saved_credentials saved={0};n=sizeof(saved);
    if(nvs_get_blob(h,"wifi_current",&saved,&n)==ESP_OK&&n==sizeof(saved)&&
       memchr(saved.ssid,0,sizeof(saved.ssid))&&memchr(saved.password,0,sizeof(saved.password))&&
       wifi_credentials_valid(saved.ssid,saved.password,saved.password[0]!=0)){
        strcpy(ssid,saved.ssid);strcpy(password,saved.password);
    }
    memset(&saved,0,sizeof(saved));nvs_close(h);
    size_t length=strlen(server);if(length&&server[length-1]=='/')server[length-1]=0;
}
static esp_err_t store_wifi(nvs_handle_t h,const char *name,const char *secret){
    wifi_saved_credentials saved={0};snprintf(saved.ssid,sizeof(saved.ssid),"%s",name);snprintf(saved.password,sizeof(saved.password),"%s",secret);
    esp_err_t err=nvs_set_blob(h,"wifi_current",&saved,sizeof(saved));memset(&saved,0,sizeof(saved));return err;
}
static lv_obj_t *label(lv_obj_t *parent,const char *text,const lv_font_t *font,int x,int y){
    lv_obj_t *o=lv_label_create(parent);lv_label_set_text(o,text);lv_obj_set_style_text_font(o,font,0);lv_obj_set_style_text_color(o,lv_color_hex(0xdde9ee),0);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);return o;
}
static bool request_wifi(const wifi_ui_command *command){return wifi_commands&&xQueueSend(wifi_commands,command,0)==pdTRUE;}
static void request_setup(void){atomic_store(&setup_requested,true);}
static void display_init(void){
    bsp_display_start();bsp_display_lock(-1);screen=lv_screen_active();screen_ui_create(request_setup,request_wifi);bsp_display_unlock();
}
static void draw(void){
    if(atomic_load(&setup_active))return;
    bsp_display_lock(-1);if(!atomic_load(&setup_active))screen_ui_update(&last,fetched,state,last_received);bsp_display_unlock();
}
static void wifi_event(void *arg,esp_event_base_t base,int32_t id,void *data){
    (void)arg;(void)data;
    if(base==IP_EVENT&&id==IP_EVENT_STA_GOT_IP){xEventGroupSetBits(network,1);ESP_LOGI("pixora","Wi-Fi station acquired IP");}
    if(base==WIFI_EVENT&&id==WIFI_EVENT_STA_DISCONNECTED){xEventGroupClearBits(network,1);const wifi_event_sta_disconnected_t *event=data;ESP_LOGW("pixora","Wi-Fi disconnected (reason %u)",event?(unsigned)event->reason:0);}
}
static const char form[]=
"<!doctype html><html lang=en><meta name=viewport content='width=device-width,initial-scale=1'><meta name=referrer content=no-referrer><title>Pixora Setup</title>"
"<style>body{font:17px system-ui;max-width:480px;margin:30px auto;padding:20px;background:#f3f0e8;color:#132c28}input,button,select{box-sizing:border-box;width:100%;font:inherit;padding:14px;margin:10px 0 22px}small{display:block}summary{padding:16px 0}</style>"
"<h1>Pixora</h1><p>连接你的 Wi-Fi / Connect Wi-Fi</p><label>附近的 2.4GHz 网络 / Nearby networks<select id=networks><option value=>扫描中 / Scanning…</option></select></label><button id=scan type=button>重新扫描 / Scan again</button><small id=scan-status role=status></small><form method=post action=/save><input type=hidden name=csrf value=\"%s\"><label>Wi-Fi 名称（可手动填写隐藏网络）/ SSID<input id=ssid name=ssid maxlength=32 required autocomplete=off></label>"
"<label>Wi-Fi 密码 / Password<input name=password type=password maxlength=64 autocomplete=off></label>"
"<details><summary>高级连接设置 / Advanced</summary><small>已配对设备可留空。New devices require a scoped display token, never an admin or collector key.</small>"
"<label>服务地址 / HTTPS server<input name=server type=url maxlength=240 placeholder='https://your-pixora.example'></label>"
"<label>显示令牌 / Display token<input name=token type=password maxlength=128 autocomplete=off></label></details>"
"<button>保存并连接 / Save and connect</button></form><p><script src=/setup.js defer></script>2.4 GHz Wi-Fi only. If connection fails, tap Wi-Fi / Setup on the screen, then scan its new code.</p></html>";
static bool ap_request(httpd_req_t *r){
    struct sockaddr_storage local={0};socklen_t length=sizeof(local);
    if(!atomic_load(&setup_active)||getsockname(httpd_req_to_sockfd(r),(struct sockaddr*)&local,&length)!=0)return false;
    if(local.ss_family==AF_INET&&length>=sizeof(struct sockaddr_in)){
        const struct sockaddr_in *v4=(const struct sockaddr_in*)&local;
        return setup_address_allowed((const unsigned char*)&v4->sin_addr,4);
    }
    if(local.ss_family==AF_INET6&&length>=sizeof(struct sockaddr_in6)){
        const struct sockaddr_in6 *v6=(const struct sockaddr_in6*)&local;
        return setup_address_allowed((const unsigned char*)&v6->sin6_addr,16);
    }
    return false;
}
static esp_err_t form_get(httpd_req_t *r){
    if(!ap_request(r))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Join device setup Wi-Fi first");
    httpd_resp_set_type(r,"text/html; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_set_hdr(r,"Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'");
    const char *marker=strstr(form,"%s");
    if(!marker)return ESP_FAIL;
    if(httpd_resp_send_chunk(r,form,marker-form)!=ESP_OK)return ESP_FAIL;
    if(httpd_resp_send_chunk(r,setup_nonce,strlen(setup_nonce))!=ESP_OK)return ESP_FAIL;
    if(httpd_resp_send_chunk(r,marker+2,strlen(marker+2))!=ESP_OK)return ESP_FAIL;
    return httpd_resp_send_chunk(r,NULL,0);
}
static const char setup_js[]=
"const list=document.querySelector('#networks'),ssid=document.querySelector('#ssid'),button=document.querySelector('#scan'),status=document.querySelector('#scan-status');"
"list.addEventListener('change',()=>{if(list.value)ssid.value=list.value;});"
"async function scan(){button.disabled=true;status.textContent='正在扫描 / Scanning…';try{const r=await fetch('/networks',{cache:'no-store'});if(!r.ok)throw Error();const rows=await r.json();list.replaceChildren(new Option('选择网络或手动填写 / Select or enter manually',''));for(const n of rows){list.add(new Option(n.ssid+' · '+n.rssi+' dBm · '+(n.secure?'加密 / Secured':'开放 / Open'),n.ssid));}status.textContent=rows.length?'仅列出 2.4GHz 网络 / 2.4GHz networks only':'未发现网络，可重新扫描或手动填写 / No networks found';}catch(e){status.textContent='扫描失败，请重试或手动填写 / Scan failed; retry or enter manually';}finally{button.disabled=false;}}button.addEventListener('click',scan);scan();";
static esp_err_t script_get(httpd_req_t *r){
    if(!ap_request(r))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Join device setup Wi-Fi first");
    httpd_resp_set_type(r,"application/javascript; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    return httpd_resp_send(r,setup_js,HTTPD_RESP_USE_STRLEN);
}
static esp_err_t networks_get(httpd_req_t *r){
    if(!ap_request(r))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Join device setup Wi-Fi first");
    wifi_scan_config_t config={0};config.scan_type=WIFI_SCAN_TYPE_ACTIVE;
    config.scan_time.active.min=40;config.scan_time.active.max=100;
    if(esp_wifi_scan_start(&config,true)!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Scan failed; retry");
    uint16_t count=24;wifi_ap_record_t *rows=calloc(count,sizeof(*rows));
    if(!rows){esp_wifi_clear_ap_list();return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Not enough memory");}
    if(esp_wifi_scan_get_ap_records(&count,rows)!=ESP_OK){free(rows);esp_wifi_clear_ap_list();return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Scan unavailable");}
    cJSON *result=cJSON_CreateArray();
    for(int i=0;result&&i<count;i++){
        rows[i].ssid[32]=0;if(!rows[i].ssid[0]||!strcmp((char*)rows[i].ssid,ap_name))continue;
        bool duplicate=false;for(int j=0;j<i;j++)if(!strcmp((char*)rows[j].ssid,(char*)rows[i].ssid))duplicate=true;
        if(duplicate)continue;
        cJSON *item=cJSON_CreateObject();if(!item)continue;
        cJSON_AddStringToObject(item,"ssid",(char*)rows[i].ssid);cJSON_AddNumberToObject(item,"rssi",rows[i].rssi);
        cJSON_AddBoolToObject(item,"secure",rows[i].authmode!=WIFI_AUTH_OPEN);cJSON_AddItemToArray(result,item);
    }
    free(rows);char *json=result?cJSON_PrintUnformatted(result):NULL;cJSON_Delete(result);
    if(!json)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Scan unavailable");
    httpd_resp_set_type(r,"application/json; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    esp_err_t err=httpd_resp_sendstr(r,json);free(json);return err;
}
static bool decode(char *s){
    char *w=s;
    for(char *p=s;*p;p++){
        if(*p=='+')*w++=' ';
        else if(*p=='%'){
            if(!p[1]||!p[2]||!isxdigit((unsigned char)p[1])||!isxdigit((unsigned char)p[2]))return false;
            char hex[3]={p[1],p[2],0};int c=(int)strtol(hex,NULL,16);if(!c)return false;*w++=(char)c;p+=2;
        }else *w++=*p;
    }*w=0;return true;
}
static void restart_task(void *arg){(void)arg;vTaskDelay(pdMS_TO_TICKS(1500));esp_restart();}
static esp_err_t form_save(httpd_req_t *r){
    if(!ap_request(r))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Join device setup Wi-Fi first");
    // A no-referrer form can submit Origin: null in mobile browsers.
    // A per-boot form nonce is mandatory even when Origin is absent/null.
    char origin[80]={0};size_t origin_length=httpd_req_get_hdr_value_len(r,"Origin");
    if(origin_length&&(httpd_req_get_hdr_value_str(r,"Origin",origin,sizeof(origin))!=ESP_OK||
       !setup_origin_allowed(origin)))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Reopen setup page on device Wi-Fi");
    if(r->content_len<=0||r->content_len>2048)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Form too large");
    char body[2049];int offset=0;
    while(offset<r->content_len){int n=httpd_req_recv(r,body+offset,r->content_len-offset);if(n<=0)return ESP_FAIL;offset+=n;}body[offset]=0;
    char next_ssid[33]={0},next_pass[65]={0},next_server[257]={0},next_token[129]={0},csrf[33]={0};int mask=0;char *save=NULL;
    for(char *p=strtok_r(body,"&",&save);p;p=strtok_r(NULL,"&",&save)){
        char *value=strchr(p,'=');if(!value)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid form");*value++=0;
        if(!decode(value))return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid encoding");
        int bit=0;char *dest=NULL;size_t size=0;
        if(!strcmp(p,"ssid")){bit=1;dest=next_ssid;size=sizeof(next_ssid);}
        else if(!strcmp(p,"password")){bit=2;dest=next_pass;size=sizeof(next_pass);}
        else if(!strcmp(p,"server")){bit=4;dest=next_server;size=sizeof(next_server);}
        else if(!strcmp(p,"token")){bit=8;dest=next_token;size=sizeof(next_token);}
        else if(!strcmp(p,"csrf")){bit=16;dest=csrf;size=sizeof(csrf);}
        if(!bit||(mask&bit)||strlen(value)>=size)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid field");
        strcpy(dest,value);mask|=bit;
    }
    if(!(mask&16)||!setup_nonce_valid(csrf,setup_nonce))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Setup page expired; reload and try again");
    if(!wifi_credentials_valid(next_ssid,next_pass,next_pass[0]!=0))return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Use a 1-32 byte Wi-Fi name and 8-63 ASCII password (or 64 hex digits); leave password empty for open networks");
    // Keep secrets out of HTML and logs; empty advanced fields preserve provisioning.
    char old_server[257],old_token[129];strcpy(old_server,server);strcpy(old_token,token);
    size_t new_length=strlen(next_server);if(new_length&&next_server[new_length-1]=='/')next_server[new_length-1]=0;
    if(next_server[0]&&strcmp(next_server,server)&&!next_token[0])return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Changing server requires its own display token");
    if(next_server[0])strcpy(server,next_server);
    if(next_token[0])strcpy(token,next_token);
    size_t length=strlen(server);if(length&&server[length-1]=='/')server[length-1]=0;
    if(!config_valid()){strcpy(server,old_server);strcpy(token,old_token);return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"HTTPS server and scoped display token required");}
    nvs_handle_t h;esp_err_t err=nvs_open("pixora",NVS_READWRITE,&h);
    if(err==ESP_OK){err=store_wifi(h,next_ssid,next_pass);if(err==ESP_OK)err=nvs_set_str(h,"server",server);if(err==ESP_OK)err=nvs_set_str(h,"token",token);if(err==ESP_OK)err=nvs_commit(h);nvs_close(h);}
    memset(next_pass,0,sizeof(next_pass));memset(next_token,0,sizeof(next_token));memset(body,0,sizeof(body));
    if(err!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Could not save");
    httpd_resp_set_type(r,"text/html; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_sendstr(r,"<meta name=viewport content='width=device-width,initial-scale=1'><h2>Saved / 已保存</h2><p>屏幕正在连接，稍后请让手机重新连接原 Wi-Fi。</p>");
    xTaskCreate(restart_task,"restart",2048,NULL,1,NULL);return ESP_OK;
}
static void setup_start(void){
    if(atomic_exchange(&setup_active,true))return;
    for(int i=0;i<16;i++)snprintf(setup_nonce+i*2,3,"%02x",(unsigned)(esp_random()&255));
    unsigned id=(unsigned)(esp_random()&0xffff);snprintf(ap_name,sizeof(ap_name),"Pixora-%04X",id);
    const char chars[]="abcdefghjkmnpqrstuvwxyz23456789";for(int i=0;i<16;i++)ap_pass[i]=chars[esp_random()%(sizeof(chars)-1)];ap_pass[16]=0;
    wifi_config_t ap={0};strcpy((char*)ap.ap.ssid,ap_name);strcpy((char*)ap.ap.password,ap_pass);ap.ap.ssid_len=strlen(ap_name);ap.ap.max_connection=1;ap.ap.authmode=WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&ap));
    httpd_config_t cfg=HTTPD_DEFAULT_CONFIG();cfg.stack_size=8192;cfg.max_open_sockets=3;cfg.lru_purge_enable=true;
    httpd_handle_t http=NULL;ESP_ERROR_CHECK(httpd_start(&http,&cfg));
    httpd_uri_t get={.uri="/",.method=HTTP_GET,.handler=form_get},post={.uri="/save",.method=HTTP_POST,.handler=form_save};httpd_register_uri_handler(http,&get);httpd_register_uri_handler(http,&post);
    httpd_uri_t js={.uri="/setup.js",.method=HTTP_GET,.handler=script_get},scan={.uri="/networks",.method=HTTP_GET,.handler=networks_get};
    httpd_register_uri_handler(http,&js);httpd_register_uri_handler(http,&scan);
    bsp_display_lock(-1);screen_ui_pause();lv_obj_clean(screen);
    label(screen,"Pixora Setup",&lv_font_montserrat_24,0,15);
    label(screen,"1. Scan to join device Wi-Fi",&lv_font_montserrat_18,0,57);
    lv_obj_t *qr=lv_qrcode_create(screen);lv_qrcode_set_size(qr,210);lv_qrcode_set_dark_color(qr,lv_color_black());lv_qrcode_set_light_color(qr,lv_color_white());lv_obj_align(qr,LV_ALIGN_TOP_MID,0,92);
    char wifi[140];snprintf(wifi,sizeof(wifi),"WIFI:T:WPA;S:%s;P:%s;;",ap_name,ap_pass);lv_qrcode_update(qr,wifi,strlen(wifi));
    label(screen,ap_name,&lv_font_montserrat_18,0,315);label(screen,ap_pass,&lv_font_montserrat_18,0,345);
    label(screen,"2. Open http://192.168.4.1",&lv_font_montserrat_18,0,389);
    label(screen,"Set 2.4 GHz Wi-Fi, then Save",&lv_font_montserrat_14,0,428);bsp_display_unlock();
}
static void read_quota(void){
    char url[300],authorization[145];snprintf(url,sizeof(url),"%s/api/v1/device",server);snprintf(authorization,sizeof(authorization),"Bearer %s",token);
    esp_http_client_config_t cfg={.url=url,.timeout_ms=12000,.crt_bundle_attach=esp_crt_bundle_attach,.disable_auto_redirect=true,.buffer_size=2048};
    esp_http_client_handle_t c=esp_http_client_init(&cfg);if(!c){state="NETWORK ERROR";last.stale=true;return;}
    esp_http_client_set_header(c,"Authorization",authorization);esp_http_client_set_header(c,"Accept","application/json");
    char *body=malloc(16385);int size=0;bool valid=false;
    if(body&&esp_http_client_open(c,0)==ESP_OK){
        esp_http_client_fetch_headers(c);int status=esp_http_client_get_status_code(c);
        if(status==401||status==403){memset(&last,0,sizeof(last));fetched=false;state="PAIR AGAIN";}
        else if(status==200){
            while(size<16385){int n=esp_http_client_read(c,body+size,16385-size);if(n<0)break;if(!n){valid=esp_http_client_is_complete_data_received(c);break;}size+=n;}
            quota_view next;if(valid&&quota_parse(body,size,time(NULL),&next)){last=next;fetched=true;last_received=time(NULL);ESP_LOGI("pixora","Authenticated device response accepted (%s)",next.stale?"stale":"fresh");state=!(next.primary.known||next.weekly.known)?"NO QUOTA DATA":next.stale?"STALE / CACHED":"CONNECTED";}
            else{last.stale=true;state="INVALID DATA / CACHED";}
        }else{last.stale=true;state="SERVER ERROR / CACHED";}
    }else{last.stale=true;state="NETWORK ERROR / CACHED";}
    if(body){memset(body,0,16385);free(body);}esp_http_client_cleanup(c);memset(authorization,0,sizeof(authorization));
}
static void native_scan(void){
    if(!(xEventGroupGetBits(network)&1)){esp_wifi_disconnect();vTaskDelay(pdMS_TO_TICKS(150));}
    wifi_scan_config_t config={0};config.scan_type=WIFI_SCAN_TYPE_ACTIVE;config.scan_time.active.min=40;config.scan_time.active.max=100;
    wifi_ui_network list[WIFI_UI_LIMIT]={0};unsigned used=0;const char *message="No networks. Scan again or enter hidden SSID.";
    if(esp_wifi_scan_start(&config,true)==ESP_OK){
        uint16_t count=24;wifi_ap_record_t *records=calloc(count,sizeof(*records));
        if(records&&esp_wifi_scan_get_ap_records(&count,records)==ESP_OK){
            for(int i=0;i<count&&used<WIFI_UI_LIMIT;i++){
                records[i].ssid[32]=0;if(!records[i].ssid[0]||!strcmp((char*)records[i].ssid,ap_name))continue;
                bool duplicate=false;for(unsigned j=0;j<used;j++)if(!strcmp(list[j].ssid,(char*)records[i].ssid))duplicate=true;if(duplicate)continue;
                wifi_ui_network *entry=&list[used++];strcpy(entry->ssid,(char*)records[i].ssid);entry->rssi=records[i].rssi;entry->secure=records[i].authmode!=WIFI_AUTH_OPEN;
                wifi_auth_mode_t auth=records[i].authmode;entry->supported=auth==WIFI_AUTH_OPEN||auth==WIFI_AUTH_WPA_PSK||auth==WIFI_AUTH_WPA2_PSK||auth==WIFI_AUTH_WPA_WPA2_PSK||auth==WIFI_AUTH_WPA3_PSK||auth==WIFI_AUTH_WPA2_WPA3_PSK;
            }
            if(used)message="Select a network / scroll for more";
        }else message="Scan unavailable. Please retry.";
        free(records);esp_wifi_clear_ap_list();
    }else message="Scan busy. Please retry in a moment.";
    bsp_display_lock(-1);screen_ui_wifi_scan_result(list,used,message);bsp_display_unlock();
}
static esp_err_t set_station(const char *name,const char *secret){
    wifi_config_t config={0};memcpy(config.sta.ssid,name,strlen(name));memcpy(config.sta.password,secret,strlen(secret));
    // Match the selected security class without falling back from a password to open Wi-Fi.
    config.sta.threshold.authmode=secret[0]?WIFI_AUTH_WPA_PSK:WIFI_AUTH_OPEN;
    config.sta.sae_pwe_h2e=WPA3_SAE_PWE_BOTH;config.sta.pmf_cfg.capable=true;
    esp_wifi_disconnect();xEventGroupClearBits(network,1);vTaskDelay(pdMS_TO_TICKS(150));
    esp_err_t err=esp_wifi_set_config(WIFI_IF_STA,&config);memset(&config,0,sizeof(config));
    return err==ESP_OK?esp_wifi_connect():err;
}
static void native_connect(wifi_ui_command *command){
    bool ok=false;const char *message="Invalid network/password. Previous Wi-Fi kept.";
    if(wifi_credentials_valid(command->ssid,command->password,command->secure)){
        state="CONNECTING NEW WI-FI";last.stale=true;
        wifi_ap_record_t connected_ap={0};
        if(set_station(command->ssid,command->password)==ESP_OK&&
           (xEventGroupWaitBits(network,1,pdFALSE,pdFALSE,pdMS_TO_TICKS(18000))&1)&&
           esp_wifi_sta_get_ap_info(&connected_ap)==ESP_OK&&!strncmp((char*)connected_ap.ssid,command->ssid,32)){
            nvs_handle_t h;esp_err_t err=nvs_open("pixora",NVS_READWRITE,&h);
            if(err==ESP_OK){err=store_wifi(h,command->ssid,command->password);if(err==ESP_OK)err=nvs_commit(h);nvs_close(h);}
            if(err==ESP_OK){strcpy(ssid,command->ssid);strcpy(password,command->password);ok=true;message="Connected and saved. Return to Orbit.";state="WI-FI CONNECTED";}
            else message="Could not save. Old settings kept; reconnecting.";
        }else message=ssid[0]?"Connection failed. Old settings kept; reconnecting. Check password and 2.4GHz Wi-Fi.":"Connection failed. Check password and 2.4GHz Wi-Fi, then retry.";
        if(!ok){if(ssid[0]){set_station(ssid,password);state="RESTORING PREVIOUS WI-FI";}else{esp_wifi_disconnect();state="CHECK WI-FI / SETUP";}}
    }
    memset(command,0,sizeof(*command));bsp_display_lock(-1);screen_ui_wifi_connect_result(ok,message);bsp_display_unlock();
}
static void collector(void *arg){
    (void)arg;int failures=0,ticks=0;
    while(true){
        if(atomic_exchange(&setup_requested,false))setup_start();
        if(atomic_load(&setup_active)){vTaskDelay(pdMS_TO_TICKS(1000));continue;}
        wifi_ui_command command={0};
        if(xQueueReceive(wifi_commands,&command,0)==pdTRUE){
            if(command.kind==WIFI_UI_SCAN)native_scan();
            else if(command.kind==WIFI_UI_CONNECT){native_connect(&command);ticks=0;}
            memset(&command,0,sizeof(command));
        }
        if(!(xEventGroupGetBits(network)&1)){
            state="WI-FI OFFLINE / CACHED";last.stale=true;draw();esp_wifi_connect();
            if(!(xEventGroupWaitBits(network,1,pdFALSE,pdFALSE,pdMS_TO_TICKS(12000))&1)){failures++;if(failures==2){
                esp_err_t legacy=esp_wifi_set_protocol(WIFI_IF_STA,WIFI_PROTOCOL_11B|WIFI_PROTOCOL_11G);
                esp_wifi_set_bandwidth(WIFI_IF_STA,WIFI_BW_HT20);esp_wifi_set_ps(WIFI_PS_NONE);
                ESP_LOGW("pixora","Trying legacy 2.4GHz radio compatibility (result %d)",(int)legacy);
            }if(failures>=3){state="CHECK WI-FI / SETUP";draw();}vTaskDelay(pdMS_TO_TICKS(3000));continue;}
            failures=0;ticks=0;
        }
        if(time(NULL)<1700000000){state="SYNCING TIME";draw();vTaskDelay(pdMS_TO_TICKS(1000));continue;}
        if(!ticks){read_quota();ticks=30;}
        if(fetched&&quota_expired(&last,time(NULL))&&last_received&&!strcmp(state,"CONNECTED"))state="STALE / CACHED";
        draw();ticks--;vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
void app_main(void){
    setenv("TZ","UTC0",1);tzset();
    // Never erase user NVS automatically on an initialization error.
    ESP_ERROR_CHECK(nvs_flash_init());load_config();wifi_commands=xQueueCreate(1,sizeof(wifi_ui_command));assert(wifi_commands);display_init();
    ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());network=xEventGroupCreate();esp_netif_create_default_wifi_sta();esp_netif_create_default_wifi_ap();
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,WIFI_EVENT_STA_DISCONNECTED,wifi_event,NULL));ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,IP_EVENT_STA_GOT_IP,wifi_event,NULL));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));wifi_config_t sta={0};memcpy(sta.sta.ssid,ssid,strlen(ssid));memcpy(sta.sta.password,password,strlen(password));sta.sta.threshold.authmode=password[0]?WIFI_AUTH_WPA_PSK:WIFI_AUTH_OPEN;sta.sta.sae_pwe_h2e=WPA3_SAE_PWE_BOTH;sta.sta.pmf_cfg.capable=true;ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&sta));ESP_ERROR_CHECK(esp_wifi_start());ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    if(ssid[0]){
        wifi_scan_config_t scan={0};scan.ssid=(uint8_t*)ssid;scan.show_hidden=true;
        if(esp_wifi_scan_start(&scan,true)==ESP_OK){
            uint16_t count=4;wifi_ap_record_t found[4]={0};
            if(esp_wifi_scan_get_ap_records(&count,found)==ESP_OK){
                ESP_LOGI("pixora","Configured target scan matches: %u",(unsigned)count);
                for(int i=0;i<count;i++)ESP_LOGI("pixora","Target radio: auth=%u channel=%u RSSI=%d",(unsigned)found[i].authmode,(unsigned)found[i].primary,found[i].rssi);
            }
            esp_wifi_clear_ap_list();
        }
    }
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);esp_sntp_setservername(0,"pool.ntp.org");esp_sntp_init();
    if(!config_valid())setup_start();
    else if(!ssid[0]){bsp_display_lock(-1);screen_ui_open_wifi();bsp_display_unlock();}
    xTaskCreate(collector,"pixora-poll",12288,NULL,3,NULL);
}
