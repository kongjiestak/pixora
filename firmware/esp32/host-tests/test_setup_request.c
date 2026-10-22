#include <assert.h>
#include <stdio.h>
#include "setup_request.h"
int main(void){
 const char *nonce="0123456789abcdef0123456789abcdef";
 assert(setup_origin_allowed("http://192.168.4.1"));
 assert(setup_origin_allowed("null"));assert(setup_origin_allowed(""));
 assert(!setup_origin_allowed("https://evil.example"));
 assert(!setup_origin_allowed("http://192.168.4.1.evil.example"));
 assert(!setup_origin_allowed("http://192.168.4.1:81"));
 assert(setup_nonce_valid(nonce,nonce));
 assert(!setup_nonce_valid("",nonce));assert(!setup_nonce_valid(NULL,nonce));
 assert(!setup_nonce_valid("0123456789abcdef0123456789abcdee",nonce));
 assert(!setup_nonce_valid("0123456789abcdef0123456789abcdefx",nonce));
 puts("Setup Origin and form nonce tests passed");
}
