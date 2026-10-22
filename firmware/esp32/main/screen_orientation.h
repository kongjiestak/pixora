#pragma once
#include <stdbool.h>
typedef struct {bool swap_xy,mirror_x,mirror_y;} screen_touch_flags;
/* Match absolute MADCTL, not the BSP init table's 0xA0 default.
 * 0x00: identity; 0x60: swap+MX; 0xC0: MX+MY; 0xA0: swap+MY.
 * Touch library mirrors before swapping. Panel is the sole rotation owner;
 * adapter stays at zero. Entries correspond to 0/90/180/270. */
static inline screen_touch_flags screen_touch_flags_for_rotation(unsigned quarter){
    static const screen_touch_flags flags[]={
        {false,false,false},{true,true,false},
        {false,true,true},{true,false,true}
    };
    return flags[quarter<4?quarter:0];
}
