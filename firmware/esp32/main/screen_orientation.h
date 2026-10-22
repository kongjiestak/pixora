#pragma once
#include <stdbool.h>
typedef struct {bool swap_xy,mirror_x,mirror_y;} screen_touch_flags;
/* Native panel: logical=(479-raw_y,raw_x). The touch library mirrors
 * before swapping. Panel MADCTL is the sole display rotation owner; the
 * LVGL adapter must remain at zero. Entries correspond to 0/90/180/270. */
static inline screen_touch_flags screen_touch_flags_for_rotation(unsigned quarter){
    static const screen_touch_flags flags[]={
        {true,false,true},{false,false,false},
        {true,true,false},{false,true,true}
    };
    return flags[quarter<4?quarter:0];
}
