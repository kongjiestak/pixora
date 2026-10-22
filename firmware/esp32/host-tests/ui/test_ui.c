#include "lvgl.h"
#include "screen_ui.h"
#include "display_input.h"
#include "screen_i18n.h"
#include "nvs.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static time_t epoch=1792679400;
static unsigned elapsed;
static lv_indev_t *pointer;
static uint16_t framebuffer[480*480];
static bool pressed;
static lv_point_t point;
static struct {char key[24];int32_t value;} storage[24];
static unsigned count;
time_t time(time_t *out){if(out)*out=epoch;return epoch;}
int64_t esp_timer_get_time(void){return (int64_t)elapsed*1000;}
void esp_restart(void){abort();}
static unsigned dark_frames;static int panel_brightness,min_brightness=100;
esp_err_t bsp_display_brightness_set(int percent){assert(percent>=0&&percent<=100);panel_brightness=percent;if(percent<min_brightness)min_brightness=percent;if(!percent)dark_frames++;return ESP_OK;}
lv_indev_t *pixora_display_get_input_dev(void){return pointer;}
esp_err_t nvs_open(const char *name,int mode,nvs_handle_t *h){(void)name;(void)mode;*h=1;return ESP_OK;}
void nvs_close(nvs_handle_t h){(void)h;}
esp_err_t nvs_commit(nvs_handle_t h){(void)h;return ESP_OK;}
esp_err_t nvs_set_i32(nvs_handle_t h,const char *key,int32_t value){(void)h;unsigned i=0;for(;i<count;i++)if(!strcmp(storage[i].key,key))break;if(i==count){assert(count<24);strcpy(storage[count++].key,key);}storage[i].value=value;return ESP_OK;}
esp_err_t nvs_get_i32(nvs_handle_t h,const char *key,int32_t *value){(void)h;for(unsigned i=0;i<count;i++)if(!strcmp(storage[i].key,key)){*value=storage[i].value;return ESP_OK;}return -1;}
esp_err_t nvs_set_u8(nvs_handle_t h,const char *key,uint8_t value){return nvs_set_i32(h,key,value);}
esp_err_t nvs_get_u8(nvs_handle_t h,const char *key,uint8_t *value){int32_t v;int e=nvs_get_i32(h,key,&v);if(!e)*value=v;return e;}
static void read_pointer(lv_indev_t *input,lv_indev_data_t *data){(void)input;data->point=point;data->state=pressed?LV_INDEV_STATE_PRESSED:LV_INDEV_STATE_RELEASED;}
static void flush(lv_display_t *display,const lv_area_t *area,uint8_t *pixels){
 const uint16_t *source=(const uint16_t*)pixels;int width=area->x2-area->x1+1;
 for(int y=area->y1;y<=area->y2;y++)for(int x=area->x1;x<=area->x2;x++)framebuffer[y*480+x]=source[(y-area->y1)*width+x-area->x1];
 lv_display_flush_ready(display);
}
static void image(const char *path){FILE *f=fopen(path,"wb");assert(f);fprintf(f,"P6\n480 480\n255\n");for(unsigned i=0;i<480*480;i++){uint16_t p=framebuffer[i];unsigned char rgb[]={(p>>11)*255/31,((p>>5)&63)*255/63,(p&31)*255/31};fwrite(rgb,1,3,f);}fclose(f);}
static void pump(unsigned ms){for(unsigned i=0;i<ms;i+=10){elapsed+=10;if(elapsed%1000==0)epoch++;lv_tick_inc(10);lv_timer_handler();}}
static lv_obj_t *find(lv_obj_t *parent,const char *value){if(lv_obj_has_flag(parent,LV_OBJ_FLAG_HIDDEN))return NULL;if(lv_obj_check_type(parent,&lv_label_class)&&!strcmp(lv_label_get_text(parent),value))return parent;for(unsigned i=0;i<lv_obj_get_child_count(parent);i++){lv_obj_t *r=find(lv_obj_get_child(parent,i),value);if(r)return r;}return NULL;}
static void click(const char *value){lv_obj_t *label=find(lv_screen_active(),value);if(!label){fprintf(stderr,"Missing control: %s\n",value);abort();}lv_obj_update_layout(lv_screen_active());lv_area_t a;lv_obj_get_coords(label,&a);point=(lv_point_t){(a.x1+a.x2)/2,(a.y1+a.y2)/2};pressed=true;pump(90);pressed=false;pump(150);}
static unsigned cached_images(lv_obj_t *obj){
 if(lv_obj_has_flag(obj,LV_OBJ_FLAG_HIDDEN))return 0;
 unsigned n=0;if(lv_obj_check_type(obj,&lv_image_class)){assert(lv_image_get_src(obj));n++;}
 for(unsigned i=0;i<lv_obj_get_child_count(obj);i++)n+=cached_images(lv_obj_get_child(obj,i));return n;
}
static void swipe(void){point=(lv_point_t){340,240};pressed=true;pump(60);point.x=250;pump(40);point.x=140;pump(40);pressed=false;pump(500);}
static void moving_images(lv_obj_t *obj,lv_obj_t **images,unsigned *count){
 if(lv_obj_has_flag(obj,LV_OBJ_FLAG_HIDDEN))return;
 if(lv_obj_check_type(obj,&lv_image_class)&&lv_obj_get_width(obj)==480){assert(*count<2);images[(*count)++]=obj;}
 for(unsigned i=0;i<lv_obj_get_child_count(obj);i++)moving_images(lv_obj_get_child(obj,i),images,count);
}
static void probe_swipe(bool left){
 point=(lv_point_t){left?340:140,240};pressed=true;pump(60);point.x=250;pump(40);point.x=left?140:340;pump(40);pressed=false;pump(80);
 lv_obj_t *images[2]={0};unsigned count=0;moving_images(lv_screen_active(),images,&count);assert(count==2);
 int old_x=lv_obj_get_x(images[0]),new_x=lv_obj_get_x(images[1]);assert(left?(old_x<0&&new_x>0):(old_x>0&&new_x<0));assert(abs(old_x-new_x)==480);
 assert(panel_brightness==60);image("/tmp/pixora-ui-slide-midpoint.ppm");pump(500);count=0;moving_images(lv_screen_active(),images,&count);assert(count==0);
}
static void setup(void){}
static bool wifi(const wifi_ui_command *c){(void)c;return true;}
static void usb(bool on){(void)on;}
static bool ble_state;
static void ble(bool on){ble_state=on;}
int main(void){
 setenv("TZ","UTC0",1);tzset();lv_init();lv_display_t *d=lv_display_create(480,480);static uint8_t buffer[480*PIXORA_DRAW_ROWS*2];lv_display_set_buffers(d,buffer,NULL,sizeof(buffer),LV_DISPLAY_RENDER_MODE_PARTIAL);lv_display_set_flush_cb(d,flush);lv_display_add_event_cb(d,pixora_display_align_area,LV_EVENT_INVALIDATE_AREA,NULL);
 pointer=lv_indev_create();lv_indev_set_type(pointer,LV_INDEV_TYPE_POINTER);lv_indev_set_read_cb(pointer,read_pointer);
 nvs_set_u8(1,"ui_clock",1);screen_ui_create(setup,wifi,usb,ble);pump(500);
 assert(find(lv_screen_active(),":"));assert(cached_images(lv_screen_active())==4);image("/tmp/pixora-ui-digital.ppm");
 for(unsigned i=0;i<4;i++){click(LV_SYMBOL_SETTINGS);assert(find(lv_screen_active(),"Pixora / Settings"));click(i?"Theme / paper":"Theme / orbit");click("paper");assert(find(lv_screen_active(),"Theme / paper"));click("Back to Orbit");assert(find(lv_screen_active(),":"));}
 click(LV_SYMBOL_SETTINGS);click("Screen / Clock");click("Language / English");assert(find(lv_screen_active(),"语言 / 简体中文"));image("/tmp/pixora-ui-zh-settings.ppm");click("返回");click("返回显示");assert(find(lv_screen_active(),"秒"));
 uint8_t lang=0;assert(nvs_get_u8(1,"ui_lang",&lang)==ESP_OK&&lang==1);
 lv_obj_t *colon=find(lv_screen_active(),":");assert(colon);lv_opa_t before=lv_obj_get_style_text_opa(colon,LV_PART_MAIN);pump(1000);assert(lv_obj_get_style_text_opa(colon,LV_PART_MAIN)!=before);
 click(LV_SYMBOL_SETTINGS);click("屏幕与时钟");click("语言 / 简体中文");click("Back");click("Back to Orbit");assert(nvs_get_u8(1,"ui_lang",&lang)==ESP_OK&&lang==0);
 quota_view fixture={.collected_at=epoch,.primary={.known=true,.remaining=84},.weekly={.known=true,.remaining=98},.activity={.state=1,.expires_at=epoch+60}};
 screen_ui_update(&fixture,true,"MAC USB / CONNECTED",epoch,true);pump(100);
 click(LV_SYMBOL_SETTINGS);click("Connection / Source");assert(find(lv_screen_active(),"Connection / Source"));
 click("Mac BLE / OFF");assert(ble_state);uint8_t saved_ble=0;
 assert(nvs_get_u8(1,"ble_bridge",&saved_ble)==ESP_OK&&saved_ble==1);
 click("Mac BLE / ON");assert(!ble_state);
 lv_area_t ble_area,back_area;lv_obj_get_coords(lv_obj_get_parent(find(lv_screen_active(),"Mac BLE / OFF")),&ble_area);
 lv_obj_get_coords(lv_obj_get_parent(find(lv_screen_active(),"Back to Orbit")),&back_area);assert(ble_area.y2<back_area.y1);
 image("/tmp/pixora-ui-ble-source.ppm");click("Back to Orbit");
 unsigned before_dark=dark_frames;min_brightness=60;probe_swipe(true);assert(dark_frames==before_dark&&min_brightness==60&&panel_brightness==60);assert(find(lv_screen_active(),"Working"));image("/tmp/pixora-ui-bot.ppm");
 probe_swipe(false);assert(find(lv_screen_active(),":"));probe_swipe(true);assert(find(lv_screen_active(),"Working"));
 for(unsigned i=0;i<18;i++){swipe();assert(find(lv_screen_active(),i%3==0?"CODEX":i%3==1?":":"Working"));}
 pump(1100);uint8_t saved_face=0;assert(nvs_get_u8(1,"ui_face",&saved_face)==ESP_OK&&saved_face==2);assert(cached_images(lv_screen_active())==4);
 pump(61000);assert(find(lv_screen_active(),"Activity unknown"));click(LV_SYMBOL_SETTINGS);assert(find(lv_screen_active(),"Pixora / Settings"));
 assert(find(lv_screen_active(),"Connection / Source"));image("/tmp/pixora-ui-visible-source-entry.ppm");
 click("Motion / ON");click("Back to Orbit");before_dark=dark_frames;swipe();assert(dark_frames==before_dark&&panel_brightness==60);assert(find(lv_screen_active(),"CODEX"));
 puts("PASS: directional snapshot slides, constant brightness, motion off, cached three-face carousel, task-state expiry, real LVGL pointer navigation, four Paper menu cycles, bilingual persistence and per-second digital clock blink");return 0;
}
