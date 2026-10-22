#include "ble_wire.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
    uint8_t fixture[256];size_t n=0;unsigned value;
    while(fscanf(f,"%2x",&value)==1){assert(n<sizeof(fixture));fixture[n++]=(uint8_t)value;}
    fclose(f);assert(n>36);
    ble_wire_buffer *b=calloc(1,sizeof(*b));assert(b);
    uint8_t out[256];size_t written=99;char token[33];memset(token,'A',32);token[32]=0;
    for(size_t split=1;split<n;split++){
        ble_wire_reset(b);assert(ble_wire_feed(b,fixture,split)==0);
        assert(ble_wire_feed(b,fixture+split,n-split)==1);
        assert(ble_wire_open(b,token,out,sizeof(out),&written));
        const char expected[]="Pixora synthetic BLE fixture";
        assert(written==sizeof(expected)-1&&!memcmp(out,expected,sizeof(expected)-1));
    }
    for(size_t i=0;i<n;i++){
        uint8_t corrupt[256];memcpy(corrupt,fixture,n);corrupt[i]^=1;
        ble_wire_reset(b);int result=ble_wire_feed(b,corrupt,n);
        assert(result!=1||!ble_wire_open(b,token,out,sizeof(out),&written));
    }
    ble_wire_reset(b);assert(ble_wire_feed(b,fixture,n)==1);
    token[0]='B';assert(!ble_wire_open(b,token,out,sizeof(out),&written));assert(written==0);
    token[0]='A';assert(!ble_wire_open(b,token,out,2,&written));
    for(size_t i=0;i<n;i++){
        ble_wire_reset(b);assert(ble_wire_feed(b,fixture,i)<1);
        assert(!ble_wire_open(b,token,out,sizeof(out),&written));
    }
    ble_wire_reset(b);uint8_t bad[20]={'P','B','L','1'};
    memset(bad+16,255,4);assert(ble_wire_feed(b,bad,20)==-1);
    assert(ble_wire_feed(b,fixture,n)==-1);
    ble_wire_reset(b);assert(ble_wire_feed(b,fixture,n)==1);
    assert(ble_wire_feed(b,fixture,1)==-1);
    free(b);puts("PASS: Python AES-GCM vector, every split, tamper, truncation, key and bounded receiver");
}
