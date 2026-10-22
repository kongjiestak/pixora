#include "screen_ui.h"
#include "theme_tokens.h"
#include "lvgl.h"
#include "nvs.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
static lv_obj_t *root,*rings[2],*center,*caption,*status,*detail,*legends[2],*satellite;
static lv_timer_t *timer;
static quota_view snapshot;
static bool has_data,paused,motion=true,settings_saved=true;
static unsigned theme,accent,focus,page;
static int64_t received;
static uint32_t cycle_started;
static char connection[64]="CONNECTING";
static void (*setup_callback)(void);
static const screen_palette *palette(void){return &screen_palettes[theme][accent];}
static void render(void);
static void persist(void){
 nvs_handle_t h;esp_err_t e=nvs_open("pixora",NVS_READWRITE,&h);
 if(e==ESP_OK){e=nvs_set_u8(h,"ui_theme",theme);if(e==ESP_OK)e=nvs_set_u8(h,"ui_accent",accent);if(e==ESP_OK)e=nvs_set_u8(h,"ui_motion",motion);if(e==ESP_OK)e=nvs_set_u8(h,"ui_focus",focus);if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);}settings_saved=e==ESP_OK;
}
static lv_obj_t *text(const char *value,const lv_font_t *font,int x,int y,uint32_t color){
 lv_obj_t *o=lv_label_create(root);lv_label_set_text(o,value);lv_obj_set_style_text_font(o,font,0);lv_obj_set_style_text_color(o,lv_color_hex(color),0);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);return o;
}
static void action(lv_event_t *event){
 unsigned id=(unsigned)(uintptr_t)lv_event_get_user_data(event);
 if(id==1)page=1;else if(id==2)page=0;else if(id==3)page=2;else if(id==4)page=3;
 else if(id==5){motion=!motion;persist();}
 else if(id==6){focus=1-focus;persist();}
 else if(id==7)page=4;
 else if(id==9)page=5;
 else if(id==8){paused=true;if(setup_callback)setup_callback();return;}
 else if(id>=20&&id<24){theme=id-20;persist();page=1;}
 else if(id>=30&&id<34){accent=id-30;persist();page=1;}
 render();
}
static void button(const char *value,int x,int y,int width,unsigned id){
 lv_obj_t *o=lv_button_create(root);lv_obj_set_size(o,width,44);lv_obj_align(o,LV_ALIGN_TOP_MID,x,y);
 lv_obj_set_style_bg_color(o,lv_color_hex(palette()->raised),0);lv_obj_set_style_shadow_width(o,0,0);lv_obj_set_style_radius(o,14,0);
 lv_obj_add_event_cb(o,action,LV_EVENT_CLICKED,(void*)(uintptr_t)id);
 lv_obj_t *t=lv_label_create(o);lv_label_set_text(t,value);lv_obj_set_style_text_font(t,&lv_font_montserrat_18,0);lv_obj_set_style_text_color(t,lv_color_hex(palette()->ink),0);lv_obj_center(t);
}
static void update_home(void){
 if(paused||page)return;
 time_t now=time(NULL);bool stale=!has_data||quota_expired(&snapshot,now);const screen_palette *p=palette();
 lv_label_set_text(status,connection);lv_obj_set_style_text_color(status,lv_color_hex(stale?p->warning:p->muted),0);
 const quota_window *slots[2]={&snapshot.primary,&snapshot.weekly};
 for(int i=0;i<2;i++){
  char value[40];if(slots[i]->known)snprintf(value,sizeof(value),"%s  %d%%",i?"LONG":"SHORT",(int)(slots[i]->remaining+.5));else snprintf(value,sizeof(value),"%s  --",i?"LONG":"SHORT");lv_label_set_text(legends[i],value);
  if(stale||!motion)lv_anim_delete(rings[i],NULL);
  int target=slots[i]->known?(int)(slots[i]->remaining+.5):0;
  if(lv_arc_get_value(rings[i])!=target){lv_anim_delete(rings[i],NULL);if(motion&&has_data&&!stale){lv_anim_t anim;lv_anim_init(&anim);lv_anim_set_var(&anim,rings[i]);lv_anim_set_values(&anim,lv_arc_get_value(rings[i]),target);lv_anim_set_duration(&anim,900);lv_anim_set_path_cb(&anim,lv_anim_path_ease_in_out);lv_anim_set_exec_cb(&anim,(lv_anim_exec_xcb_t)lv_arc_set_value);lv_anim_start(&anim);}else lv_arc_set_value(rings[i],target);}
  lv_obj_set_style_arc_color(rings[i],lv_color_hex(stale?p->warning:(i?p->secondary:p->accent)),LV_PART_INDICATOR);
 }
 const quota_window *w=slots[focus];char value[64];if(w->known)snprintf(value,sizeof(value),"%d%%",(int)(w->remaining+.5));else strcpy(value,"--");lv_label_set_text(center,value);lv_label_set_text(caption,focus?"LONG WINDOW / remaining":"SHORT WINDOW / remaining");
 char age[40];if(snapshot.collected_at&&now>=snapshot.collected_at)snprintf(age,sizeof(age),"Collected %lldm ago",(long long)((now-snapshot.collected_at)/60));else strcpy(age,"No collected data");
 char reset[40];if(w->known&&w->resets_at&&now>1700000000){long long m=(w->resets_at-now+59)/60;if(m<0)m=0;snprintf(reset,sizeof(reset),"Reset %lldh %lldm",m/60,m%60);}else strcpy(reset,"Reset --");
 snprintf(value,sizeof(value),"%s%s\n%s",age,stale?" / STALE":"",reset);lv_label_set_text(detail,value);
 lv_obj_set_style_text_color(center,lv_color_hex(p->ink),0);
}
static void tick(lv_timer_t *t){
 (void)t;if(paused||page)return;
 bool healthy=has_data&&!quota_expired(&snapshot,time(NULL))&&!strcmp(connection,"CONNECTED");
 if(motion&&healthy){uint32_t elapsed=lv_tick_get()-cycle_started;int angle=(elapsed%30000)*360/30000;lv_arc_set_angles(satellite,angle,angle+2);lv_obj_remove_flag(satellite,LV_OBJ_FLAG_HIDDEN);}else lv_obj_add_flag(satellite,LV_OBJ_FLAG_HIDDEN);
}
static void render(void){
 const screen_palette *p=palette();lv_obj_clean(root);lv_obj_set_style_bg_color(root,lv_color_hex(p->ground),0);lv_obj_remove_flag(root,LV_OBJ_FLAG_SCROLLABLE);
 lv_obj_set_style_bg_grad_color(root,lv_color_hex(p->raised),0);lv_obj_set_style_bg_grad_dir(root,theme==3?LV_GRAD_DIR_VER:LV_GRAD_DIR_NONE,0);
 if(page){
  text(page==4?"Connect Wi-Fi?":page==5?"Connection / Source":"Pixora / Settings",&lv_font_montserrat_24,0,28,p->ink);
  if(page==1){char value[60];snprintf(value,sizeof(value),"Theme / %s",screen_theme_names[theme]);button(value,0,94,340,3);snprintf(value,sizeof(value),"Accent / %s",screen_accent_names[accent]);button(value,0,150,340,4);button(motion?"Motion / ON":"Motion / OFF",0,206,340,5);button("Wi-Fi setup...",0,262,340,7);text(settings_saved?"Settings saved on this screen":"Save failed; please retry",&lv_font_montserrat_14,0,325,p->muted);}
  if(page==2||page==3)for(unsigned i=0;i<4;i++)button(page==2?screen_theme_names[i]:screen_accent_names[i],0,90+i*58,320,(page==2?20:30)+i);
  if(page==4){text("This pauses the status display.",&lv_font_montserrat_18,0,115,p->muted);text("Existing Wi-Fi is kept until Save.",&lv_font_montserrat_18,0,152,p->muted);button("Open phone setup",0,230,330,8);}
  if(page==5){
   text(connection,&lv_font_montserrat_18,0,94,p->ink);text("Transport / Wi-Fi + HTTPS",&lv_font_montserrat_18,0,144,p->muted);text("Source / Codex App Server",&lv_font_montserrat_18,0,184,p->muted);
   char stamp[60];time_t collected=snapshot.collected_at;struct tm utc;
   if(collected&&gmtime_r(&collected,&utc))strftime(stamp,sizeof(stamp),"Collected / %m-%d %H:%M UTC",&utc);else strcpy(stamp,"No collected data");text(stamp,&lv_font_montserrat_18,0,224,p->muted);
   text("Motion indicates poll rhythm only.",&lv_font_montserrat_14,0,284,p->muted);text("It does not mean AI is running.",&lv_font_montserrat_14,0,310,p->muted);
  }
  button(page==1||page==5?"Back to Orbit":"Back",0,384,280,page==1||page==5?2:1);return;
 }
 text("Pixora",&lv_font_montserrat_24,-132,20,p->ink);button("Settings",143,14,110,1);
 status=text(connection,&lv_font_montserrat_14,0,65,p->muted);lv_obj_add_flag(status,LV_OBJ_FLAG_CLICKABLE);lv_obj_set_ext_click_area(status,12);lv_obj_add_event_cb(status,action,LV_EVENT_CLICKED,(void*)9);
 for(int i=0;i<2;i++){
  rings[i]=lv_arc_create(root);int size=310-i*44;lv_obj_set_size(rings[i],size,size);lv_obj_align(rings[i],LV_ALIGN_TOP_MID,0,96+i*22);lv_arc_set_range(rings[i],0,100);lv_arc_set_rotation(rings[i],270);lv_arc_set_bg_angles(rings[i],0,360);lv_arc_set_value(rings[i],0);lv_obj_remove_style(rings[i],NULL,LV_PART_KNOB);lv_obj_remove_flag(rings[i],LV_OBJ_FLAG_CLICKABLE);lv_obj_set_style_arc_width(rings[i],8,LV_PART_MAIN);lv_obj_set_style_arc_width(rings[i],8,LV_PART_INDICATOR);lv_obj_set_style_arc_color(rings[i],lv_color_hex(p->track),LV_PART_MAIN);
 }
 satellite=lv_arc_create(root);lv_obj_set_size(satellite,334,334);lv_obj_align(satellite,LV_ALIGN_TOP_MID,0,84);lv_arc_set_bg_angles(satellite,0,360);lv_obj_set_style_arc_opa(satellite,LV_OPA_TRANSP,LV_PART_MAIN);lv_obj_set_style_arc_color(satellite,lv_color_hex(p->muted),LV_PART_INDICATOR);lv_obj_set_style_arc_width(satellite,4,LV_PART_INDICATOR);lv_obj_remove_style(satellite,NULL,LV_PART_KNOB);lv_obj_remove_flag(satellite,LV_OBJ_FLAG_CLICKABLE);lv_obj_add_flag(satellite,LV_OBJ_FLAG_HIDDEN);
 text("CODEX",&lv_font_montserrat_18,0,163,p->muted);
 center=text("--",&lv_font_montserrat_48,0,204,p->ink);lv_obj_add_flag(center,LV_OBJ_FLAG_CLICKABLE);lv_obj_set_ext_click_area(center,18);lv_obj_add_event_cb(center,action,LV_EVENT_CLICKED,(void*)6);
 caption=text("SHORT WINDOW / remaining",&lv_font_montserrat_14,0,267,p->muted);
 detail=text("No collected data",&lv_font_montserrat_14,0,300,p->muted);lv_obj_set_style_text_align(detail,LV_TEXT_ALIGN_CENTER,0);
 legends[0]=text("SHORT --",&lv_font_montserrat_18,-102,435,p->accent);legends[1]=text("LONG --",&lv_font_montserrat_18,102,435,p->secondary);
 update_home();
}
void screen_ui_create(void (*request_setup)(void)){
 setup_callback=request_setup;root=lv_screen_active();paused=false;page=0;
 nvs_handle_t h;if(nvs_open("pixora",NVS_READONLY,&h)==ESP_OK){uint8_t v;if(nvs_get_u8(h,"ui_theme",&v)==ESP_OK&&v<4)theme=v;if(nvs_get_u8(h,"ui_accent",&v)==ESP_OK&&v<4)accent=v;if(nvs_get_u8(h,"ui_motion",&v)==ESP_OK)motion=!!v;if(nvs_get_u8(h,"ui_focus",&v)==ESP_OK&&v<2)focus=v;nvs_close(h);}
 render();if(!timer)timer=lv_timer_create(tick,100,NULL);
}
void screen_ui_update(const quota_view *view,bool fetched,const char *state,int64_t latest){
 if(latest!=received){received=latest;cycle_started=lv_tick_get();}snapshot=*view;has_data=fetched;snprintf(connection,sizeof(connection),"%s",state);update_home();
}
void screen_ui_pause(void){paused=true;lv_anim_delete_all();}
