#include "ble_wire.h"
#include <string.h>
#include "mbedtls/gcm.h"
#include "mbedtls/sha256.h"
#include "mbedtls/platform_util.h"
void ble_wire_reset(ble_wire_buffer *b){if(b)memset(b,0,sizeof(*b));}
int ble_wire_feed(ble_wire_buffer *b,const uint8_t *chunk,size_t size){
    if(!b||b->failed)return -1;
    if(!chunk||!size||size>BLE_WIRE_MAX-b->used)goto reject;
    memcpy(b->bytes+b->used,chunk,size);b->used+=size;
    if(b->used>=4&&memcmp(b->bytes,"PBL1",4))goto reject;
    if(b->used>=BLE_WIRE_HEADER){
        uint32_t n=((uint32_t)b->bytes[16]<<24)|((uint32_t)b->bytes[17]<<16)|((uint32_t)b->bytes[18]<<8)|b->bytes[19];
        if(!n||n>BLE_WIRE_MAX_PLAIN)goto reject;
        b->expected=BLE_WIRE_HEADER+n+BLE_WIRE_TAG;
        if(b->used>b->expected)goto reject;
    }
    return b->expected&&b->used==b->expected?1:0;
reject:b->failed=true;return -1;
}
bool ble_wire_open(const ble_wire_buffer *b,const char *token,uint8_t *out,size_t capacity,size_t *written){
    if(written)*written=0;
    if(!b||!token||!out||!written||b->failed||!b->expected||b->used!=b->expected)return false;
    size_t n=b->used-BLE_WIRE_HEADER-BLE_WIRE_TAG,len=strnlen(token,129);
    if(len<32||len>128||capacity<n)return false;
    for(size_t i=0;i<len;i++)if(!((token[i]>='a'&&token[i]<='z')||(token[i]>='A'&&token[i]<='Z')||(token[i]>='0'&&token[i]<='9')||token[i]=='_'||token[i]=='-'))return false;
    static const char prefix[]="Pixora BLE v1 key";
    uint8_t material[sizeof(prefix)+128]={0},key[32];
    memcpy(material,prefix,sizeof(prefix));memcpy(material+sizeof(prefix),token,len);
    int result=mbedtls_sha256(material,sizeof(prefix)+len,key,0);
    mbedtls_platform_zeroize(material,sizeof(material));
    mbedtls_gcm_context g;mbedtls_gcm_init(&g);
    if(!result)result=mbedtls_gcm_setkey(&g,MBEDTLS_CIPHER_ID_AES,key,256);
    if(!result)result=mbedtls_gcm_auth_decrypt(&g,n,b->bytes+4,12,b->bytes,BLE_WIRE_HEADER,
        b->bytes+BLE_WIRE_HEADER+n,BLE_WIRE_TAG,b->bytes+BLE_WIRE_HEADER,out);
    mbedtls_gcm_free(&g);mbedtls_platform_zeroize(key,sizeof(key));
    if(result){mbedtls_platform_zeroize(out,n);return false;}
    *written=n;return true;
}
