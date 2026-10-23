#include "pixel_pet.h"
#include <string.h>
static void box(lv_draw_buf_t *b,int x,int y,int w,int h,uint32_t color){
 for(int yy=y*4;yy<(y+h)*4;yy++){
  if(yy<0||yy>=PIXORA_PET_HEIGHT)continue;
  uint32_t *row=(uint32_t *)(b->data+yy*b->header.stride);
  for(int xx=x*4;xx<(x+w)*4;xx++)if(xx>=0&&xx<PIXORA_PET_WIDTH)row[xx]=0xff000000|color;
 }
}
static uint32_t tint(uint32_t c,unsigned light){
 unsigned r=(c>>16)&255,g=(c>>8)&255,b=c&255;
 return ((r+(255-r)*light/100)<<16)|((g+(255-g)*light/100)<<8)|(b+(255-b)*light/100);
}
void pixel_pet_draw(lv_draw_buf_t *b,unsigned state,unsigned pose,bool greeting,uint32_t accent){
 memset(b->data,0,b->header.stride*PIXORA_PET_HEIGHT);
 const uint32_t ink=0x142140,face=0x182e59,shine=0x8ff4ff;
 uint32_t shell=tint(accent,18),light=tint(accent,48);int arm=(greeting||state==1)?(pose&1)*3:0;
 /* Block-stepped silhouette: cloud helmet, compact body, boots. */
 box(b,16,2,14,3,ink);box(b,9,5,29,4,ink);box(b,5,9,37,5,ink);box(b,2,14,43,15,ink);box(b,5,29,37,6,ink);box(b,10,35,28,3,ink);
 box(b,16,3,14,4,light);box(b,10,6,27,5,light);box(b,6,10,35,7,shell);box(b,3,15,41,13,shell);box(b,6,28,35,5,accent);box(b,11,33,26,3,accent);
 box(b,7,13,34,17,ink);box(b,9,15,30,13,face);box(b,10,16,28,2,0x203963);
 box(b,15,37,18,13,ink);box(b,17,38,14,10,shell);box(b,17,38,14,2,light);
 box(b,10,39-arm,6,10,ink);box(b,11,40-arm,4,7,shell);box(b,32,39+arm,6,10,ink);box(b,33,40+arm,4,7,accent);
 box(b,14,49,8,5,ink);box(b,27,49,8,5,ink);box(b,15,49,6,3,accent);box(b,28,49,6,3,accent);
 box(b,20,42,2,1,shine);box(b,22,43,2,1,shine);box(b,20,44,2,1,shine);box(b,26,44,3,1,shine);
 if(greeting){ /* A wave is a local reaction, never a task state. */
  box(b,33,34-arm,4,10,ink);box(b,34,35-arm,2,8,light);box(b,37,30-arm,3,5,shine);
  box(b,14,21,5,2,shine);box(b,29,21,5,2,shine);box(b,20,25,9,1,shine);
 }else if(state==0){
  box(b,14,22,5,1,shine);box(b,29,22,5,1,shine);box(b,23,25,3,1,shine);
  box(b,39,4,5,1,light);box(b,42,5,1,1,light);box(b,39,6,5,1,light);
 }else if(state==3){
  for(int i=0;i<4;i++){box(b,14+i,19+i,1,1,0xffadad);box(b,17-i,19+i,1,1,0xffadad);}
  box(b,29,20,4,2,0xffadad);box(b,21,25,8,1,0xffadad);
  box(b,39,2,2,4,0xffadad);box(b,39,7,2,1,0xffadad);
 }else if(pose==4){box(b,14,22,5,1,shine);box(b,29,22,5,1,shine);}
 else{
  box(b,14,19,2,2,shine);box(b,16,21,2,2,shine);box(b,14,23,2,2,shine);box(b,28,23,7,2,shine);
  if(state==1){box(b,8,49,32,2,ink);box(b,10,48,28,1,light);box(b,12+(pose%4)*6,50,4,1,shine);}
 }
}
