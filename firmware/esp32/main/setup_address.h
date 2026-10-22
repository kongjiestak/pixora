#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
// ESP-IDF's dual-stack HTTP listener reports IPv4 clients as mapped IPv6.
// Match the local AP destination, never the peer or an arbitrary LAN address.
static inline bool setup_address_allowed(const unsigned char *address,size_t length){
    static const unsigned char ap[4]={192,168,4,1};
    static const unsigned char mapped_prefix[12]={0,0,0,0,0,0,0,0,0,0,255,255};
    if(!address)return false;
    if(length==4)return memcmp(address,ap,4)==0;
    return length==16&&memcmp(address,mapped_prefix,12)==0&&memcmp(address+12,ap,4)==0;
}
