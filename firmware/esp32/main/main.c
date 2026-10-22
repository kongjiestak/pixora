#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <stdatomic.h>
#include <ctype.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_http_server.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "esp_sntp.h"
#include "lwip/sockets.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "lvgl.h"
#include "bsp/esp-bsp.h"
#include "quota.h"

// Private configuration is provisioned in NVS, never built into the firmware.
static char ssid[33],password[65],server[257],token[129];
static EventGroupHandle_t network;
static atomic_bool setup_active;
static lv_obj_t *status_label,*age_label,*percent[2],*arcs[2],*reset[2],*screen;
static quota_view last;
static bool fetched;
static const char *state="CONNECTING";
static char ap_name[32],ap_pass[17];
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
    nvs_close(h);
    size_t length=strlen(server);if(length&&server[length-1]=='/')server[length-1]=0;
}
static lv_obj_t *label(lv_obj_t *parent,const char *text,const lv_font_t *font,int x,int y){
    lv_obj_t *o=lv_label_create(parent);lv_label_set_text(o,text);lv_obj_set_style_text_font(o,font,0);lv_obj_set_style_text_color(o,lv_color_hex(0xdde9ee),0);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);return o;
}
static void settings_event(lv_event_t *e){(void)e;setup_start();}
static void display_init(void){
    bsp_display_start();bsp_display_lock(-1);screen=lv_screen_active();lv_obj_set_style_bg_color(screen,lv_color_hex(0x071116),0);
    lv_obj_remove_flag(screen,LV_OBJ_FLAG_SCROLLABLE);
    label(screen,"Pixora",&lv_font_montserrat_24,0,20);
    label(screen,"CODEX",&lv_font_montserrat_32,0,67);
    status_label=label(screen,"CONNECTING",&lv_font_montserrat_18,0,114);
    for(int i=0;i<2;i++){
        int x=i?111:-111;
        arcs[i]=lv_arc_create(screen);lv_obj_set_size(arcs[i],186,186);lv_obj_align(arcs[i],LV_ALIGN_TOP_MID,x,174);
        lv_arc_set_range(arcs[i],0,100);lv_arc_set_rotation(arcs[i],270);lv_arc_set_bg_angles(arcs[i],0,360);
        lv_arc_set_value(arcs[i],0);lv_obj_remove_style(arcs[i],NULL,LV_PART_KNOB);lv_obj_remove_flag(arcs[i],LV_OBJ_FLAG_CLICKABLE);
        lv_obj_set_style_arc_width(arcs[i],9,LV_PART_MAIN);lv_obj_set_style_arc_width(arcs[i],9,LV_PART_INDICATOR);
        lv_obj_set_style_arc_color(arcs[i],lv_color_hex(0x253a46),LV_PART_MAIN);
        label(screen,i?"LONG WINDOW":"SHORT WINDOW",&lv_font_montserrat_14,x,151);
        percent[i]=label(screen,"--",&lv_font_montserrat_48,x,230);
        label(screen,"remaining",&lv_font_montserrat_14,x,291);
        reset[i]=label(screen,"Reset --",&lv_font_montserrat_14,x,361);
    }
    age_label=label(screen,"No collected data",&lv_font_montserrat_14,0,382);
    lv_obj_t *button=lv_button_create(screen);lv_obj_set_size(button,170,42);lv_obj_align(button,LV_ALIGN_BOTTOM_MID,0,-14);
    lv_obj_add_event_cb(button,settings_event,LV_EVENT_CLICKED,NULL);label(button,"Wi-Fi / Setup",&lv_font_montserrat_14,0,10);
    bsp_display_unlock();
}
static void draw(void){
    if(atomic_load(&setup_active))return;
    time_t epoch=time(NULL);bool stale=!fetched||quota_expired(&last,epoch);
    bsp_display_lock(-1);if(atomic_load(&setup_active)){bsp_display_unlock();return;}lv_label_set_text(status_label,state);
    lv_color_t color=lv_color_hex(stale?0xe5bd70:0x7ee2c0);
    lv_obj_set_style_text_color(status_label,color,0);
    quota_window *slots[2]={&last.primary,&last.weekly};
    for(int i=0;i<2;i++){
        char text[16];if(slots[i]->known)snprintf(text,sizeof(text),"%d%%",(int)(slots[i]->remaining+0.5));else strcpy(text,"--");
        lv_label_set_text(percent[i],text);
        char countdown[40];if(slots[i]->known&&slots[i]->resets_at){long long minutes=(slots[i]->resets_at-epoch+59)/60;if(minutes<0)minutes=0;if(minutes>=1440)snprintf(countdown,sizeof(countdown),"Reset %lldd %lldh",minutes/1440,(minutes%1440)/60);else snprintf(countdown,sizeof(countdown),"Reset %lldh %lldm",minutes/60,minutes%60);}else strcpy(countdown,"Reset --");lv_label_set_text(reset[i],countdown);lv_arc_set_value(arcs[i],slots[i]->known?(int)(slots[i]->remaining+0.5):0);lv_obj_set_style_arc_color(arcs[i],color,LV_PART_INDICATOR);
    }
    char text[100];if(last.collected_at&&epoch>=last.collected_at)snprintf(text,sizeof(text),"Collected %lld min ago%s",(long long)((epoch-last.collected_at)/60),stale?" - STALE":"");else strcpy(text,"No collected data");
    lv_label_set_text(age_label,text);bsp_display_unlock();
}
static void wifi_event(void *arg,esp_event_base_t base,int32_t id,void *data){
    (void)arg;(void)data;
    if(base==IP_EVENT&&id==IP_EVENT_STA_GOT_IP)xEventGroupSetBits(network,1);
    if(base==WIFI_EVENT&&id==WIFI_EVENT_STA_DISCONNECTED)xEventGroupClearBits(network,1);
}
static const char form[]=
"<!doctype html><html lang=en><meta name=viewport content='width=device-width,initial-scale=1'><meta name=referrer content=no-referrer><title>Pixora Setup</title>"
"<style>body{font:17px system-ui;max-width:480px;margin:30px auto;padding:20px;background:#f3f0e8;color:#132c28}input,button{box-sizing:border-box;width:100%;font:inherit;padding:14px;margin:10px 0 22px}small{display:block}summary{padding:16px 0}</style>"
"<h1>Pixora</h1><p>连接你的 Wi-Fi / Connect Wi-Fi</p><form method=post action=/save><label>Wi-Fi 名称 / SSID<input name=ssid maxlength=32 required></label>"
"<label>Wi-Fi 密码 / Password<input name=password type=password maxlength=64 autocomplete=off></label>"
"<details><summary>高级连接设置 / Advanced</summary><small>已配对设备可留空。New devices require a scoped display token, never an admin or collector key.</small>"
"<label>服务地址 / HTTPS server<input name=server type=url maxlength=240 placeholder='https://your-pixora.example'></label>"
"<label>显示令牌 / Display token<input name=token type=password maxlength=128 autocomplete=off></label></details>"
"<button>保存并连接 / Save and connect</button></form><p>2.4 GHz Wi-Fi only. If connection fails, tap Wi-Fi / Setup on the screen, then scan its new code.</p></html>";
static bool ap_request(httpd_req_t *r){
    struct sockaddr_in local={0};socklen_t length=sizeof(local);
    return atomic_load(&setup_active)&&getsockname(httpd_req_to_sockfd(r),(struct sockaddr*)&local,&length)==0&&local.sin_family==AF_INET&&local.sin_addr.s_addr==inet_addr("192.168.4.1");
}
static esp_err_t form_get(httpd_req_t *r){
    if(!ap_request(r))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Join device setup Wi-Fi first");
    httpd_resp_set_type(r,"text/html; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_set_hdr(r,"Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'");
    return httpd_resp_send(r,form,HTTPD_RESP_USE_STRLEN);
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
    char origin[80];if(httpd_req_get_hdr_value_str(r,"Origin",origin,sizeof(origin))!=ESP_OK||strcmp(origin,"http://192.168.4.1"))return httpd_resp_send_err(r,HTTPD_403_FORBIDDEN,"Open setup page from device Wi-Fi");
    if(r->content_len<=0||r->content_len>2048)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Form too large");
    char body[2049];int offset=0;
    while(offset<r->content_len){int n=httpd_req_recv(r,body+offset,r->content_len-offset);if(n<=0)return ESP_FAIL;offset+=n;}body[offset]=0;
    char next_ssid[33]={0},next_pass[65]={0},next_server[257]={0},next_token[129]={0};int mask=0;char *save=NULL;
    for(char *p=strtok_r(body,"&",&save);p;p=strtok_r(NULL,"&",&save)){
        char *value=strchr(p,'=');if(!value)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid form");*value++=0;
        if(!decode(value))return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid encoding");
        int bit=0;char *dest=NULL;size_t size=0;
        if(!strcmp(p,"ssid")){bit=1;dest=next_ssid;size=sizeof(next_ssid);}
        else if(!strcmp(p,"password")){bit=2;dest=next_pass;size=sizeof(next_pass);}
        else if(!strcmp(p,"server")){bit=4;dest=next_server;size=sizeof(next_server);}
        else if(!strcmp(p,"token")){bit=8;dest=next_token;size=sizeof(next_token);}
        if(!bit||(mask&bit)||strlen(value)>=size)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid field");
        strcpy(dest,value);mask|=bit;
    }
    if(!next_ssid[0])return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Wi-Fi name required");
    // Keep secrets out of HTML and logs; empty advanced fields preserve provisioning.
    char old_server[257],old_token[129];strcpy(old_server,server);strcpy(old_token,token);
    size_t new_length=strlen(next_server);if(new_length&&next_server[new_length-1]=='/')next_server[new_length-1]=0;
    if(next_server[0]&&strcmp(next_server,server)&&!next_token[0])return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Changing server requires its own display token");
    if(next_server[0])strcpy(server,next_server);
    if(next_token[0])strcpy(token,next_token);
    size_t length=strlen(server);if(length&&server[length-1]=='/')server[length-1]=0;
    if(!config_valid()){strcpy(server,old_server);strcpy(token,old_token);return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"HTTPS server and scoped display token required");}
    nvs_handle_t h;esp_err_t err=nvs_open("pixora",NVS_READWRITE,&h);
    if(err==ESP_OK){err=nvs_set_str(h,"ssid",next_ssid);if(err==ESP_OK)err=nvs_set_str(h,"password",next_pass);if(err==ESP_OK)err=nvs_set_str(h,"server",server);if(err==ESP_OK)err=nvs_set_str(h,"token",token);if(err==ESP_OK)err=nvs_commit(h);nvs_close(h);}
    memset(next_pass,0,sizeof(next_pass));memset(next_token,0,sizeof(next_token));memset(body,0,sizeof(body));
    if(err!=ESP_OK)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"Could not save");
    httpd_resp_set_type(r,"text/html; charset=utf-8");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    httpd_resp_sendstr(r,"<meta name=viewport content='width=device-width,initial-scale=1'><h2>Saved / 已保存</h2><p>屏幕正在连接，稍后请让手机重新连接原 Wi-Fi。</p>");
    xTaskCreate(restart_task,"restart",2048,NULL,1,NULL);return ESP_OK;
}
static void setup_start(void){
    if(atomic_exchange(&setup_active,true))return;
    unsigned id=(unsigned)(esp_random()&0xffff);snprintf(ap_name,sizeof(ap_name),"Pixora-%04X",id);
    const char chars[]="abcdefghjkmnpqrstuvwxyz23456789";for(int i=0;i<16;i++)ap_pass[i]=chars[esp_random()%(sizeof(chars)-1)];ap_pass[16]=0;
    wifi_config_t ap={0};strcpy((char*)ap.ap.ssid,ap_name);strcpy((char*)ap.ap.password,ap_pass);ap.ap.ssid_len=strlen(ap_name);ap.ap.max_connection=1;ap.ap.authmode=WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&ap));
    httpd_config_t cfg=HTTPD_DEFAULT_CONFIG();cfg.stack_size=8192;cfg.max_open_sockets=3;cfg.lru_purge_enable=true;
    httpd_handle_t http=NULL;ESP_ERROR_CHECK(httpd_start(&http,&cfg));
    httpd_uri_t get={.uri="/",.method=HTTP_GET,.handler=form_get},post={.uri="/save",.method=HTTP_POST,.handler=form_save};httpd_register_uri_handler(http,&get);httpd_register_uri_handler(http,&post);
    bsp_display_lock(-1);lv_obj_clean(screen);
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
            quota_view next;if(valid&&quota_parse(body,size,time(NULL),&next)){last=next;fetched=true;last_received=time(NULL);state=!(next.primary.known||next.weekly.known)?"NO QUOTA DATA":next.stale?"STALE / CACHED":"CONNECTED";}
            else{last.stale=true;state="INVALID DATA / CACHED";}
        }else{last.stale=true;state="SERVER ERROR / CACHED";}
    }else{last.stale=true;state="NETWORK ERROR / CACHED";}
    if(body){memset(body,0,16385);free(body);}esp_http_client_cleanup(c);memset(authorization,0,sizeof(authorization));
}
static void collector(void *arg){
    (void)arg;int failures=0,ticks=0;
    while(true){
        if(atomic_load(&setup_active)){vTaskDelay(pdMS_TO_TICKS(1000));continue;}
        if(!(xEventGroupGetBits(network)&1)){
            state="WI-FI OFFLINE / CACHED";last.stale=true;draw();esp_wifi_connect();
            if(!(xEventGroupWaitBits(network,1,pdFALSE,pdFALSE,pdMS_TO_TICKS(12000))&1)){failures++;if(failures>=3){state="CHECK WI-FI / SETUP";draw();}vTaskDelay(pdMS_TO_TICKS(3000));continue;}
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
    ESP_ERROR_CHECK(nvs_flash_init());load_config();display_init();
    ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());network=xEventGroupCreate();esp_netif_create_default_wifi_sta();esp_netif_create_default_wifi_ap();
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,WIFI_EVENT_STA_DISCONNECTED,wifi_event,NULL));ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,IP_EVENT_STA_GOT_IP,wifi_event,NULL));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));wifi_config_t sta={0};memcpy(sta.sta.ssid,ssid,strlen(ssid));memcpy(sta.sta.password,password,strlen(password));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&sta));ESP_ERROR_CHECK(esp_wifi_start());
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);esp_sntp_setservername(0,"pool.ntp.org");esp_sntp_init();
    if(!ssid[0]||!config_valid())setup_start();
    xTaskCreate(collector,"pixora-poll",12288,NULL,3,NULL);
}
