#pragma once
#include "lvgl.h"
#define PIXORA_DRAW_ROWS 24
/* Application-owned input device; display rotation and DMA buffers share one port. */
lv_indev_t *pixora_display_get_input_dev(void);
/* CO5300 requires even starts and odd ends for RGB565 transfers. */
static inline void pixora_display_align_area(lv_event_t *event){
    lv_area_t *area=lv_event_get_param(event);
    area->x1&=~1;area->y1&=~1;area->x2|=1;area->y2|=1;
}
