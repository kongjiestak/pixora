#include <assert.h>
#include <stdio.h>
#include "setup_address.h"
int main(void){
    unsigned char ap[4]={192,168,4,1},lan[4]={192,168,1,1};
    unsigned char mapped[16]={0,0,0,0,0,0,0,0,0,0,255,255,192,168,4,1};
    unsigned char native[16]={0xfe,0x80};
    assert(setup_address_allowed(ap,4));
    assert(setup_address_allowed(mapped,16));
    assert(!setup_address_allowed(lan,4));
    mapped[15]=2;assert(!setup_address_allowed(mapped,16));
    assert(!setup_address_allowed(native,16));
    assert(!setup_address_allowed(NULL,4));
    for(size_t n=0;n<16;n++)if(n!=4)assert(!setup_address_allowed(ap,n));
    puts("Setup AP address guard tests passed");
}
