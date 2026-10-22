#include <assert.h>
#include <stdio.h>
#include "screen_orientation.h"
int main(void){
    const int raw[][2]={{0,0},{479,0},{0,479},{479,479},{117,179},{240,240}};
    for(unsigned r=0;r<4;r++)for(unsigned i=0;i<sizeof(raw)/sizeof(raw[0]);i++){
        int x=raw[i][0],y=raw[i][1],base_x=479-y,base_y=x;
        screen_touch_flags f=screen_touch_flags_for_rotation(r);
        if(f.mirror_x)x=479-x;
        if(f.mirror_y)y=479-y;
        if(f.swap_xy){int t=x;x=y;y=t;}
        int expected_x=base_x,expected_y=base_y;
        for(unsigned n=0;n<r;n++){int t=expected_x;expected_x=expected_y;expected_y=479-t;}
        assert(x==expected_x&&y==expected_y);
    }
    puts("PASS: touch mapping corners and measured point across four panel orientations");
}
