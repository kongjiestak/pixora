#pragma once
#include <stdbool.h>
#include <string.h>
// Absent/null Origin is allowed only alongside a valid unpredictable form nonce.
static inline bool setup_origin_allowed(const char *origin){
    return origin&&(!*origin||!strcmp(origin,"null")||!strcmp(origin,"http://192.168.4.1"));
}
static inline bool setup_nonce_valid(const char *provided,const char *expected){
    if(!provided||!expected||strlen(provided)!=32||strlen(expected)!=32)return false;
    unsigned difference=0;for(int i=0;i<32;i++)difference|=(unsigned char)provided[i]^(unsigned char)expected[i];
    return difference==0;
}
