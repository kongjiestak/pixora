#include "screen_ui.h"
#include "theme_tokens.h"
#include "lvgl.h"
#include "nvs.h"
#include "bsp/esp-bsp.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "wifi_credentials.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
static lv_obj_t *clock_label,*date_label,*weather_label,*city_label,*wake_layer,*home_controls,*page_control;
static bool clock_mode,night=true;
static unsigned brightness=60,rotation;
static int timezone_quarters=32; /* Display offset only; parser and system clock remain UTC. */
static int last_brightness=-1;
static uint32_t last_clock_tick;
static lv_obj_t *root,*rings[2],*center,*caption,*status,*detail,*legends[2];
static lv_timer_t *timer;
static quota_view snapshot;
static bool usb_source,usb_on;
static void (*usb_callback)(bool);
static bool home_dirty=true;
static bool has_data,paused,motion=true,settings_saved=true;
static unsigned theme,accent,focus,page;
static int64_t received;

static char connection[64]="CONNECTING";
static void (*setup_callback)(void);
static bool (*wifi_callback)(const wifi_ui_command *);
static wifi_ui_network wifi_rows[WIFI_UI_LIMIT];
static unsigned wifi_count;
static bool wifi_busy,chosen_secure=true;
static char chosen_ssid[33],wifi_message[96];
static lv_obj_t *wifi_input,*wifi_note;
static lv_font_t wifi_font;
static void begin_scan(void);
static void wifi_page(void);
static const screen_palette *palette(void){return &screen_palettes[theme][accent];}
static void render(void);
static void persist(void){
 nvs_handle_t h;esp_err_t e=nvs_open("pixora",NVS_READWRITE,&h);
 if(e==ESP_OK){e=nvs_set_u8(h,"ui_theme",theme);if(e==ESP_OK)e=nvs_set_u8(h,"ui_accent",accent);if(e==ESP_OK)e=nvs_set_u8(h,"ui_motion",motion);if(e==ESP_OK)e=nvs_set_u8(h,"ui_focus",focus);if(e==ESP_OK)e=nvs_set_u8(h,"usb_bridge",usb_on);if(e==ESP_OK)e=nvs_set_u8(h,"ui_clock",clock_mode);if(e==ESP_OK)e=nvs_set_u8(h,"ui_night",night);if(e==ESP_OK)e=nvs_set_u8(h,"ui_bright",brightness);if(e==ESP_OK)e=nvs_set_u8(h,"ui_rotation",rotation);if(e==ESP_OK)e=nvs_set_i32(h,"ui_tz",timezone_quarters);if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);}settings_saved=e==ESP_OK;
}
static void label_value(lv_obj_t *label,const char *value){if(strcmp(lv_label_get_text(label),value))lv_label_set_text(label,value);}
static lv_obj_t *text(const char *value,const lv_font_t *font,int x,int y,uint32_t color){
 lv_obj_t *o=lv_label_create(root);label_value(o,value);lv_obj_set_style_text_font(o,font,0);lv_obj_set_style_text_color(o,lv_color_hex(color),0);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);return o;
}
static void gesture(lv_event_t *event){
 (void)event;if(page||(wake_layer&&!lv_obj_has_flag(wake_layer,LV_OBJ_FLAG_HIDDEN)))return;lv_indev_t *input=lv_indev_active();if(!input)return;
 lv_dir_t direction=lv_indev_get_gesture_dir(input);if(direction==LV_DIR_LEFT||direction==LV_DIR_RIGHT){clock_mode=!clock_mode;persist();render();}
}
static void wake(lv_event_t *event){(void)event;lv_display_trigger_activity(NULL);if(home_controls)lv_obj_remove_flag(home_controls,LV_OBJ_FLAG_HIDDEN);if(page_control)lv_obj_remove_flag(page_control,LV_OBJ_FLAG_HIDDEN);if(wake_layer)lv_obj_add_flag(wake_layer,LV_OBJ_FLAG_HIDDEN);}
static void action(lv_event_t *event){
 unsigned id=(unsigned)(uintptr_t)lv_event_get_user_data(event);
 if(id==16)page=10;
 else if(id==17){brightness=brightness>=100?20:brightness+20;persist();}
 else if(id==18){night=!night;persist();}
 else if(id==19){clock_mode=!clock_mode;persist();page=0;}
 else if(id==40){rotation=(rotation+1)%4;persist();if(settings_saved)esp_restart();return;}
 else if(id==42){page=6;}
 else if(id==41){timezone_quarters=timezone_quarters==32?0:timezone_quarters==0?-20:32;persist();}
 else if(id==1)page=1;else if(id==2)page=0;else if(id==3)page=2;else if(id==4)page=3;
 else if(id==5){motion=!motion;persist();}
 else if(id==6){focus=1-focus;persist();}
 else if(id==7){page=6;begin_scan();return;}
 else if(id==10){page=4;}
 else if(id==11){begin_scan();return;}
 else if(id==12){chosen_ssid[0]=0;page=8;}
 else if(id==13){page=6;memset(chosen_ssid,0,sizeof(chosen_ssid));}
 else if(id>=100&&id<100+wifi_count){
  unsigned i=id-100;if(!wifi_rows[i].supported)return;strcpy(chosen_ssid,wifi_rows[i].ssid);chosen_secure=wifi_rows[i].secure;page=7;wifi_message[0]=0;
 }
 else if(id==9)page=5;
 else if(id==15){usb_on=!usb_on;persist();if(usb_callback)usb_callback(usb_on);}
 else if(id==8){paused=true;if(setup_callback)setup_callback();return;}
 else if(id>=20&&id<24){theme=id-20;persist();page=1;}
 else if(id>=30&&id<34){accent=id-30;persist();page=1;}
 render();
}
static void button(const char *value,int x,int y,int width,unsigned id){
 lv_obj_t *o=lv_button_create(root);lv_obj_set_size(o,width,44);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);
 lv_obj_set_style_bg_color(o,lv_color_hex(palette()->raised),0);lv_obj_set_style_shadow_width(o,0,0);lv_obj_set_style_radius(o,14,0);
 lv_obj_add_event_cb(o,action,LV_EVENT_CLICKED,(void*)(uintptr_t)id);
 lv_obj_t *t=lv_label_create(o);label_value(t,value);lv_obj_set_style_text_font(t,&lv_font_montserrat_18,0);lv_obj_set_style_text_color(t,lv_color_hex(palette()->ink),0);lv_obj_center(t);
}
static void update_home(void){
 if(paused||page||clock_mode)return;
 time_t now=time(NULL);bool stale=!has_data||quota_expired(&snapshot,now);const screen_palette *p=palette();
 static quota_view shown;static char shown_connection[64];static int64_t shown_minute=-1;static bool shown_stale;
 if(!home_dirty&&shown_minute==now/60&&shown_stale==stale&&!memcmp(&shown,&snapshot,sizeof(snapshot))&&!strcmp(shown_connection,connection))return;
 home_dirty=false;shown=snapshot;shown_minute=now/60;shown_stale=stale;snprintf(shown_connection,sizeof(shown_connection),"%s",connection);

 label_value(status,connection);lv_obj_set_style_text_color(status,lv_color_hex(stale?p->warning:p->muted),0);
 const quota_window *slots[2]={&snapshot.primary,&snapshot.weekly};
 for(int i=0;i<2;i++){
  char value[40];if(slots[i]->known)snprintf(value,sizeof(value),"%s  %d%%",i?"LONG":"SHORT",(int)(slots[i]->remaining+.5));else snprintf(value,sizeof(value),"%s  --",i?"LONG":"SHORT");label_value(legends[i],value);
  if(stale||!motion)lv_anim_delete(rings[i],NULL);
  int target=slots[i]->known?(int)(slots[i]->remaining+.5):0;
  if(lv_arc_get_value(rings[i])!=target){lv_anim_delete(rings[i],NULL);if(motion&&has_data&&!stale){lv_anim_t anim;lv_anim_init(&anim);lv_anim_set_var(&anim,rings[i]);lv_anim_set_values(&anim,lv_arc_get_value(rings[i]),target);lv_anim_set_duration(&anim,350);lv_anim_set_path_cb(&anim,lv_anim_path_ease_in_out);lv_anim_set_exec_cb(&anim,(lv_anim_exec_xcb_t)lv_arc_set_value);lv_anim_start(&anim);}else lv_arc_set_value(rings[i],target);}
  lv_obj_set_style_arc_color(rings[i],lv_color_hex(stale?p->warning:(i?p->secondary:p->accent)),LV_PART_INDICATOR);
 }
 const quota_window *w=slots[focus];char value[64];if(w->known)snprintf(value,sizeof(value),"%d%%",(int)(w->remaining+.5));else strcpy(value,"--");label_value(center,value);label_value(caption,focus?"LONG WINDOW / remaining":"SHORT WINDOW / remaining");
 char age[40];if(snapshot.collected_at&&now>=snapshot.collected_at)snprintf(age,sizeof(age),"Collected %lldm ago",(long long)((now-snapshot.collected_at)/60));else strcpy(age,"No collected data");
 char reset[40];if(w->known&&w->resets_at&&now>1700000000){long long m=(w->resets_at-now+59)/60;if(m<0)m=0;snprintf(reset,sizeof(reset),"Reset %lldh %lldm",m/60,m%60);}else strcpy(reset,"Reset --");
 snprintf(value,sizeof(value),"%s%s\n%s",age,stale?" / STALE":"",reset);label_value(detail,value);
 lv_obj_set_style_text_color(center,lv_color_hex(p->ink),0);
}
static const char *weather_kind(int code){if(code==0)return "Clear";if(code<=3)return "Cloudy";if(code<=48)return "Fog";if(code<=67)return "Rain";if(code<=77)return "Snow";if(code<=86)return "Showers";return "Storm";}
static void update_clock(void){
 time_t now=time(NULL),local=now+timezone_quarters*900;struct tm tm;gmtime_r(&local,&tm);bool valid=now>1700000000;
 char value[100];snprintf(value,sizeof(value),valid?"%02d:%02d":"--:--",tm.tm_hour,tm.tm_min);label_value(clock_label,value);
 static const char *days[]={"Sun","Mon","Tue","Wed","Thu","Fri","Sat"};
 if(valid)snprintf(value,sizeof(value),"%02d/%02d  %s",tm.tm_mon+1,tm.tm_mday,days[tm.tm_wday]);else strcpy(value,"Waiting for time");label_value(date_label,value);
 const screen_weather *w=&snapshot.weather;
 if(w->known&&now<w->expires_at)snprintf(value,sizeof(value),"%s  %.0f C",weather_kind(w->code),w->temperature);
 else {snprintf(value,sizeof(value),"Weather / %s",w->present?"unavailable":"not authorized");}
 label_value(weather_label,value);
 label_value(city_label,w->known?w->city:"");
 if(clock_mode){int shift=(tm.tm_min%5)-2;lv_obj_align(clock_label,LV_ALIGN_TOP_MID,shift,166+shift);}
}
static void tick(lv_timer_t *t){
 (void)t;if(paused)return;
 time_t local=time(NULL)+timezone_quarters*900;struct tm tm;gmtime_r(&local,&tm);
 bool idle=lv_display_get_inactive_time(NULL)>15000;
 int target=(night&&time(NULL)>1700000000&&(tm.tm_hour>=22||tm.tm_hour<7)&&idle)?8:(int)brightness;
 if(target!=last_brightness&&bsp_display_brightness_set(target)==ESP_OK)last_brightness=target;
 if(page)return;
 if(idle){lv_obj_add_flag(page_control,LV_OBJ_FLAG_HIDDEN);lv_obj_add_flag(home_controls,LV_OBJ_FLAG_HIDDEN);lv_obj_remove_flag(wake_layer,LV_OBJ_FLAG_HIDDEN);}
 if(lv_tick_get()-last_clock_tick>=1000){last_clock_tick=lv_tick_get();update_clock();update_home();}
}
static void render(void){
 home_dirty=true;const screen_palette *p=palette();clock_label=NULL;wifi_input=NULL;wifi_note=NULL;lv_obj_clean(root);lv_obj_set_style_bg_color(root,lv_color_hex(p->ground),0);lv_obj_remove_flag(root,LV_OBJ_FLAG_SCROLLABLE);
 lv_obj_set_style_bg_grad_color(root,lv_color_hex(p->raised),0);lv_obj_set_style_bg_grad_dir(root,theme==3?LV_GRAD_DIR_VER:LV_GRAD_DIR_NONE,0);
 if(page>=6&&page<=9){wifi_page();return;}
 if(page){
  text(page==4?"Connect Wi-Fi?":page==5?"Connection / Source":"Pixora / Settings",&lv_font_montserrat_24,0,28,p->ink);
  if(page==1){char value[60];snprintf(value,sizeof(value),"Theme / %s",screen_theme_names[theme]);button(value,0,94,340,3);snprintf(value,sizeof(value),"Accent / %s",screen_accent_names[accent]);button(value,0,150,340,4);button(motion?"Motion / ON":"Motion / OFF",0,206,340,5);button("Wi-Fi setup...",0,262,340,7);button("Screen / Clock",0,318,340,16);}
  if(page==10){char value[80];snprintf(value,sizeof(value),"Brightness / %u%%",brightness);button(value,0,78,340,17);button(night?"Night dim / ON (22-07)":"Night dim / OFF",0,134,340,18);snprintf(value,sizeof(value),"Rotation / %u > restart",rotation*90);button(value,0,190,340,40);snprintf(value,sizeof(value),"Time / UTC%+.2f",timezone_quarters/4.0);button(value,0,246,340,41);button(clock_mode?"Open quota page":"Open bedside clock",0,302,340,19);}
  if(page==2||page==3)for(unsigned i=0;i<4;i++)button(page==2?screen_theme_names[i]:screen_accent_names[i],0,90+i*58,320,(page==2?20:30)+i);
  if(page==4){text("This pauses the status display.",&lv_font_montserrat_18,0,115,p->muted);text("Existing Wi-Fi is kept until Save.",&lv_font_montserrat_18,0,152,p->muted);button("Open phone setup",0,230,330,8);}
  if(page==5){
   text(connection,&lv_font_montserrat_18,0,94,p->ink);text(usb_source?"Transport / Mac USB bridge":"Transport / Wi-Fi + HTTPS",&lv_font_montserrat_18,0,144,p->muted);text("Source / Codex App Server",&lv_font_montserrat_18,0,184,p->muted);
   char stamp[60];time_t collected=snapshot.collected_at;struct tm utc;
   if(collected&&gmtime_r(&collected,&utc))strftime(stamp,sizeof(stamp),"Collected / %m-%d %H:%M UTC",&utc);else strcpy(stamp,"No collected data");text(stamp,&lv_font_montserrat_18,0,224,p->muted);
   text("Weather / Open-Meteo.com",&lv_font_montserrat_14,0,284,p->muted);text("CC BY 4.0 / timezone is separate",&lv_font_montserrat_14,0,310,p->muted);
   button(usb_on?"Mac USB / ON":"Mac USB / OFF",0,333,300,15);
  }
  button(page==1||page==5?"Back to Orbit":"Back",0,page==5?397:384,280,page==1||page==5?2:page==4?42:1);return;
 }
 wake_layer=NULL;home_controls=NULL;page_control=NULL;
 clock_label=text("--:--",clock_mode?&lv_font_montserrat_48:&lv_font_montserrat_24,clock_mode?0:-105,clock_mode?166:38,p->ink);
 if(clock_mode){lv_obj_set_style_transform_pivot_x(clock_label,lv_pct(50),0);lv_obj_set_style_transform_pivot_y(clock_label,lv_pct(50),0);lv_obj_set_style_transform_scale_x(clock_label,512,0);lv_obj_set_style_transform_scale_y(clock_label,512,0);}
 date_label=text("Waiting for time",&lv_font_montserrat_18,clock_mode?0:100,clock_mode?267:43,p->muted);
 weather_label=text("Weather --",&lv_font_montserrat_18,clock_mode?0:-92,clock_mode?310:385,p->ink);
 city_label=text("",&wifi_font,clock_mode?0:-92,clock_mode?339:412,p->muted);lv_obj_set_width(city_label,clock_mode?290:210);lv_label_set_long_mode(city_label,LV_LABEL_LONG_DOT);lv_obj_set_style_text_align(city_label,LV_TEXT_ALIGN_CENTER,0);
 if(!clock_mode){
 for(int i=0;i<2;i++){
  rings[i]=lv_arc_create(root);int size=286-i*40;lv_obj_set_size(rings[i],size,size);lv_obj_align(rings[i],LV_ALIGN_TOP_MID,0,91+i*20);lv_arc_set_range(rings[i],0,100);lv_arc_set_rotation(rings[i],270);lv_arc_set_bg_angles(rings[i],0,360);lv_arc_set_value(rings[i],0);lv_obj_remove_style(rings[i],NULL,LV_PART_KNOB);lv_obj_remove_flag(rings[i],LV_OBJ_FLAG_CLICKABLE);lv_obj_set_style_arc_width(rings[i],8,LV_PART_MAIN);lv_obj_set_style_arc_width(rings[i],8,LV_PART_INDICATOR);lv_obj_set_style_arc_color(rings[i],lv_color_hex(p->track),LV_PART_MAIN);
 }
 text("CODEX",&lv_font_montserrat_18,0,151,p->muted);
 center=text("--",&lv_font_montserrat_48,0,188,p->ink);lv_obj_add_flag(center,LV_OBJ_FLAG_CLICKABLE);lv_obj_set_ext_click_area(center,14);lv_obj_add_event_cb(center,action,LV_EVENT_CLICKED,(void*)6);
 caption=text("",&lv_font_montserrat_14,0,251,p->muted);
 detail=text("",&lv_font_montserrat_14,0,281,p->muted);lv_obj_set_style_text_align(detail,LV_TEXT_ALIGN_CENTER,0);
 legends[0]=text("SHORT --",&lv_font_montserrat_14,-70,337,p->accent);legends[1]=text("LONG --",&lv_font_montserrat_14,70,337,p->secondary);
 }
 status=text(connection,&lv_font_montserrat_14,clock_mode?0:102,clock_mode?370:386,p->muted);lv_obj_set_width(status,clock_mode?320:195);lv_label_set_long_mode(status,LV_LABEL_LONG_DOT);lv_obj_set_style_text_align(status,LV_TEXT_ALIGN_CENTER,0);lv_obj_add_flag(status,LV_OBJ_FLAG_CLICKABLE);lv_obj_set_ext_click_area(status,12);lv_obj_add_event_cb(status,action,LV_EVENT_CLICKED,(void*)9);
 button("Settings",100,414,132,1);home_controls=lv_obj_get_child(root,-1);
 button(clock_mode?"Quota":"Clock",-100,clock_mode?370:440,120,19); /* Repositioned below to stay inside the rounded display. */
 page_control=lv_obj_get_child(root,-1);lv_obj_align(page_control,LV_ALIGN_TOP_MID,-80,414);lv_obj_align(home_controls,LV_ALIGN_TOP_MID,80,414);
 /* A full-screen transparent shield consumes the first touch after inactivity. */
 wake_layer=lv_obj_create(root);lv_obj_set_size(wake_layer,480,480);lv_obj_center(wake_layer);lv_obj_set_style_bg_opa(wake_layer,LV_OPA_TRANSP,0);lv_obj_set_style_border_width(wake_layer,0,0);lv_obj_remove_flag(wake_layer,LV_OBJ_FLAG_SCROLLABLE);lv_obj_add_event_cb(wake_layer,wake,LV_EVENT_CLICKED,NULL);lv_obj_add_flag(wake_layer,LV_OBJ_FLAG_HIDDEN);
 update_clock();
 update_home();
}
static void refresh_measure(lv_event_t *event){
 static int64_t started,total,maximum;static unsigned samples;static bool rendered;
 if(lv_event_get_code(event)==LV_EVENT_REFR_START){started=esp_timer_get_time();rendered=false;return;}
 if(lv_event_get_code(event)==LV_EVENT_RENDER_START){rendered=true;return;}
 if(lv_event_get_code(event)!=LV_EVENT_REFR_READY||!started||!rendered)return;
 int64_t elapsed=esp_timer_get_time()-started;started=0;total+=elapsed;if(elapsed>maximum)maximum=elapsed;
 if(++samples==10){ESP_LOGI("pixora_ui","refresh samples=10 mean_ms=%lld max_ms=%lld",(long long)(total/10000),(long long)(maximum/1000));samples=0;total=maximum=0;}
}
void screen_ui_create(void (*request_setup)(void),bool (*request_wifi)(const wifi_ui_command *),void (*request_usb)(bool)){
 setup_callback=request_setup;wifi_callback=request_wifi;usb_callback=request_usb;wifi_font=lv_font_montserrat_18;wifi_font.fallback=&lv_font_simsun_16_cjk;root=lv_screen_active();paused=false;page=0;
 nvs_handle_t h;if(nvs_open("pixora",NVS_READONLY,&h)==ESP_OK){uint8_t v;if(nvs_get_u8(h,"ui_theme",&v)==ESP_OK&&v<4)theme=v;if(nvs_get_u8(h,"ui_accent",&v)==ESP_OK&&v<4)accent=v;if(nvs_get_u8(h,"ui_motion",&v)==ESP_OK)motion=!!v;if(nvs_get_u8(h,"ui_focus",&v)==ESP_OK&&v<2)focus=v;if(nvs_get_u8(h,"usb_bridge",&v)==ESP_OK)usb_on=!!v;if(nvs_get_u8(h,"ui_clock",&v)==ESP_OK)clock_mode=!!v;if(nvs_get_u8(h,"ui_night",&v)==ESP_OK)night=!!v;if(nvs_get_u8(h,"ui_bright",&v)==ESP_OK&&v>=8&&v<=100)brightness=v;if(nvs_get_u8(h,"ui_rotation",&v)==ESP_OK&&v<4)rotation=v;int32_t zone;if(nvs_get_i32(h,"ui_tz",&zone)==ESP_OK&&zone>=-48&&zone<=56)timezone_quarters=zone;nvs_close(h);}
 lv_display_add_event_cb(lv_display_get_default(),refresh_measure,LV_EVENT_REFR_START,NULL);lv_display_add_event_cb(lv_display_get_default(),refresh_measure,LV_EVENT_REFR_READY,NULL);lv_display_add_event_cb(lv_display_get_default(),refresh_measure,LV_EVENT_RENDER_START,NULL);
 lv_obj_add_event_cb(root,gesture,LV_EVENT_GESTURE,NULL);
 if(usb_callback){usb_callback(usb_on);}
 render();if(!timer)timer=lv_timer_create(tick,250,NULL);
}
void screen_ui_update(const quota_view *view,bool fetched,const char *state,int64_t latest,bool from_usb){
 usb_source=from_usb;
 if(latest!=received){received=latest;}snapshot=*view;has_data=fetched;snprintf(connection,sizeof(connection),"%s",state);update_home();if(!page&&!paused){update_clock();label_value(status,connection);}
}
void screen_ui_pause(void){paused=true;lv_anim_delete_all();}

static void begin_scan(void){
 if(wifi_busy){render();return;}
 wifi_ui_command command={.kind=WIFI_UI_SCAN};wifi_busy=true;strcpy(wifi_message,"Scanning nearby 2.4GHz Wi-Fi...");
 if(!wifi_callback||!wifi_callback(&command)){wifi_busy=false;strcpy(wifi_message,"Busy. Tap Scan to retry.");}
 render();
}
static void keyboard_event(lv_event_t *event){
 lv_event_code_t code=lv_event_get_code(event);if(!wifi_input||wifi_busy)return;
 if(code==LV_EVENT_CANCEL){lv_textarea_set_text(wifi_input,"");page=6;render();return;}
 if(code!=LV_EVENT_READY)return;
 const char *value=lv_textarea_get_text(wifi_input);
 if(page==8){
  size_t length=strlen(value);if(!length||length>32){label_value(wifi_note,"SSID must be 1-32 bytes");return;}
  strcpy(chosen_ssid,value);chosen_secure=true;page=7;render();return;
 }
 wifi_ui_command command={.kind=WIFI_UI_CONNECT,.secure=chosen_secure};
 snprintf(command.ssid,sizeof(command.ssid),"%s",chosen_ssid);snprintf(command.password,sizeof(command.password),"%s",value);
 if(!wifi_credentials_valid(command.ssid,command.password,command.secure)){
  memset(command.password,0,sizeof(command.password));label_value(wifi_note,chosen_secure?"Use 8-63 ASCII characters or 64 hex digits":"Open network: leave password empty");return;
 }
 wifi_busy=true;strcpy(wifi_message,"Connecting... previous network kept on failure");
 if(!wifi_callback||!wifi_callback(&command)){wifi_busy=false;strcpy(wifi_message,"Busy. Please try again.");}
 memset(command.password,0,sizeof(command.password));lv_textarea_set_text(wifi_input,"");
 if(wifi_busy){page=9;render();}else label_value(wifi_note,wifi_message);
}
static void wifi_page(void){
 const screen_palette *p=palette();
 if(page==6){
  text("Wi-Fi / Nearby networks",&lv_font_montserrat_24,0,20,p->ink);
  text(wifi_message,&lv_font_montserrat_14,0,55,p->muted);
  lv_obj_t *list=lv_obj_create(root);lv_obj_set_size(list,420,242);lv_obj_align(list,LV_ALIGN_TOP_MID,0,83);lv_obj_set_style_bg_opa(list,LV_OPA_TRANSP,0);lv_obj_set_style_border_width(list,0,0);lv_obj_set_style_pad_all(list,0,0);lv_obj_set_scroll_dir(list,LV_DIR_VER);
  for(unsigned i=0;i<wifi_count;i++){
   lv_obj_t *b=lv_button_create(list);lv_obj_set_size(b,412,50);lv_obj_set_pos(b,0,i*58);lv_obj_set_style_bg_color(b,lv_color_hex(p->raised),0);lv_obj_set_style_shadow_width(b,0,0);
   if(wifi_rows[i].supported&&!wifi_busy)lv_obj_add_event_cb(b,action,LV_EVENT_CLICKED,(void*)(uintptr_t)(100+i));else lv_obj_add_state(b,LV_STATE_DISABLED);
   lv_obj_t *name=lv_label_create(b);char line[100];snprintf(line,sizeof(line),"%.32s  %ddBm / %s",wifi_rows[i].ssid,wifi_rows[i].rssi,!wifi_rows[i].supported?"unsupported":wifi_rows[i].secure?"locked":"open");label_value(name,line);lv_obj_set_width(name,388);lv_label_set_long_mode(name,LV_LABEL_LONG_DOT);lv_obj_set_style_text_font(name,&wifi_font,0);lv_obj_set_style_text_color(name,lv_color_hex(p->ink),0);lv_obj_center(name);
  }
  if(!wifi_busy){button("Scan",-104,337,190,11);button("Hidden SSID",104,337,190,12);button("Phone fallback",104,393,190,10);}
  button("Back",-104,393,190,1);return;
 }
 if(page==9){
  text("Wi-Fi connection",&lv_font_montserrat_24,0,40,p->ink);text(wifi_busy?"Connecting...":"Result",&lv_font_montserrat_24,0,110,p->ink);
  lv_obj_t *message=text(wifi_message,&lv_font_montserrat_18,0,170,p->muted);lv_obj_set_width(message,380);lv_obj_set_style_text_align(message,LV_TEXT_ALIGN_CENTER,0);
  if(!wifi_busy){button("Networks",-104,337,190,13);}
  button("Back",104,337,190,1);return;
 }
 bool manual=page==8;
 text(manual?"Hidden Wi-Fi":"Wi-Fi password",&lv_font_montserrat_18,40,28,p->ink);button("Back",-157,16,100,13);
 lv_obj_t *name=text(manual?"ASCII entry; use phone for other names":chosen_ssid,&lv_font_montserrat_18,0,57,p->muted);lv_obj_set_width(name,400);lv_label_set_long_mode(name,LV_LABEL_LONG_DOT);lv_obj_set_style_text_font(name,&wifi_font,0);lv_obj_set_style_text_align(name,LV_TEXT_ALIGN_CENTER,0);
 wifi_input=lv_textarea_create(root);lv_obj_set_size(wifi_input,414,48);lv_obj_align(wifi_input,LV_ALIGN_TOP_MID,0,89);lv_textarea_set_one_line(wifi_input,true);lv_textarea_set_max_length(wifi_input,manual?32:64);lv_textarea_set_password_mode(wifi_input,!manual);lv_textarea_set_password_show_time(wifi_input,0);lv_textarea_set_accepted_chars(wifi_input," !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~");lv_obj_set_style_text_font(wifi_input,&lv_font_montserrat_18,0);lv_obj_set_style_bg_color(wifi_input,lv_color_hex(p->raised),0);lv_obj_set_style_text_color(wifi_input,lv_color_hex(p->ink),0);
 wifi_note=text(manual?"Keyboard checkmark: next / X: cancel":chosen_secure?"Checkmark: connect / X: cancel":"Open network: leave blank; tap checkmark",&lv_font_montserrat_14,0,151,p->muted);
 lv_obj_t *kb=lv_keyboard_create(root);lv_obj_set_size(kb,480,280);lv_obj_align(kb,LV_ALIGN_BOTTOM_MID,0,0);lv_keyboard_set_textarea(kb,wifi_input);lv_obj_add_event_cb(kb,keyboard_event,LV_EVENT_READY,NULL);lv_obj_add_event_cb(kb,keyboard_event,LV_EVENT_CANCEL,NULL);lv_obj_set_style_text_font(kb,&lv_font_montserrat_18,LV_PART_ITEMS);lv_obj_set_style_bg_color(kb,lv_color_hex(p->ground),0);lv_obj_set_style_bg_color(kb,lv_color_hex(p->raised),LV_PART_ITEMS);lv_obj_set_style_text_color(kb,lv_color_hex(p->ink),LV_PART_ITEMS);
}
void screen_ui_wifi_scan_result(const wifi_ui_network *rows,unsigned count,const char *message){
 wifi_busy=false;wifi_count=count>WIFI_UI_LIMIT?WIFI_UI_LIMIT:count;
 if(rows&&wifi_count)memcpy(wifi_rows,rows,wifi_count*sizeof(*rows));
 snprintf(wifi_message,sizeof(wifi_message),"%s",message);if(page==6)render();
}
void screen_ui_wifi_connect_result(bool ok,const char *message){
 (void)ok;wifi_busy=false;snprintf(wifi_message,sizeof(wifi_message),"%s",message);if(page==9)render();
}

void screen_ui_open_wifi(void){page=6;begin_scan();}
