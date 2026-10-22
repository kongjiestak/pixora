#include "usb_protocol.h"
#include "mbedtls/sha256.h"
#include "mbedtls/platform_util.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
bool usb_digest(const char *key,const char *data,size_t size,char hex[65]){
 unsigned char block[64]={0},inner[32],digest[32],pad[64];size_t length=strlen(key);int error=0;
 if(length>64){if(mbedtls_sha256((const unsigned char*)key,length,block,0))return false;}else memcpy(block,key,length);
 mbedtls_sha256_context context;mbedtls_sha256_init(&context);
 for(int i=0;i<64;i++)pad[i]=block[i]^0x36;
 error|=mbedtls_sha256_starts(&context,0);error|=mbedtls_sha256_update(&context,pad,64);error|=mbedtls_sha256_update(&context,(const unsigned char*)data,size);error|=mbedtls_sha256_finish(&context,inner);
 for(int i=0;i<64;i++)pad[i]=block[i]^0x5c;
 error|=mbedtls_sha256_starts(&context,0);error|=mbedtls_sha256_update(&context,pad,64);error|=mbedtls_sha256_update(&context,inner,32);error|=mbedtls_sha256_finish(&context,digest);mbedtls_sha256_free(&context);
 const char alphabet[]="0123456789abcdef";for(int i=0;i<32;i++){hex[i*2]=alphabet[digest[i]>>4];hex[i*2+1]=alphabet[digest[i]&15];}hex[64]=0;
 mbedtls_platform_zeroize(block,sizeof(block));mbedtls_platform_zeroize(inner,sizeof(inner));mbedtls_platform_zeroize(digest,sizeof(digest));mbedtls_platform_zeroize(pad,sizeof(pad));return error==0;
}
static bool decimal(const char *value,uint64_t *out){
 if(!*value||strlen(value)>10){return false;}
 for(const char *p=value;*p;p++)if(*p<'0'||*p>'9')return false;
 errno=0;char *end;unsigned long long n=strtoull(value,&end,10);if(errno||*end)return false;*out=n;return true;
}
bool usb_frame_parse(const char *frame,size_t length,const char *token,const char *nonce,usb_message *out){
 if(!frame||!token||!nonce||!out||length>USB_FRAME_MAX||length<120||memchr(frame,0,length)||strlen(nonce)!=32)return false;
 const char prefix[]="PXUSB1 ";if(memcmp(frame,prefix,sizeof(prefix)-1))return false;
 const char *p=frame+sizeof(prefix)-1,*limit=frame+length;char fields[4][65];
 for(int i=0;i<4;i++){const char *space=memchr(p,' ',limit-p);if(!space||space==p||space-p>64)return false;size_t n=space-p;memcpy(fields[i],p,n);fields[i][n]=0;p=space+1;}
 if(strcmp(fields[0],nonce)||strlen(fields[3])!=64)return false;
 uint64_t epoch,sequence;if(!decimal(fields[1],&epoch)||epoch<1700000000||epoch>4102444800ULL||!decimal(fields[2],&sequence)||!sequence||sequence>UINT32_MAX)return false;
 size_t body_length=limit-p;if(!body_length||body_length>16384)return false;
 char header[96];int n=snprintf(header,sizeof(header),"data %s %s %s\n",fields[0],fields[1],fields[2]);
 char *signed_data=malloc((size_t)n+body_length);if(!signed_data)return false;memcpy(signed_data,header,n);memcpy(signed_data+n,p,body_length);char expected[65]={0};bool valid=usb_digest(token,signed_data,(size_t)n+body_length,expected);free(signed_data);
 unsigned diff=0;for(int i=0;i<64;i++)diff|=(unsigned char)expected[i]^(unsigned char)fields[3][i];if(!valid||diff)return false;
 usb_message message={.epoch=(int64_t)epoch,.sequence=(uint32_t)sequence};
 if(quota_parse(p,body_length,message.epoch,&message.quota))message.kind=1;
 else{
  const char *end=NULL;cJSON *root=cJSON_ParseWithLengthOpts(p,body_length,&end,false);if(!root)return false;
  while(end<limit&&(*end==' '||*end=='\r'||*end=='\n'||*end=='\t'))end++;
  const char *event=cJSON_GetStringValue(cJSON_GetObjectItemCaseSensitive(root,"event"));
  if(end==limit&&cJSON_IsObject(root)&&cJSON_GetArraySize(root)==1&&event){if(!strcmp(event,"revoked"))message.kind=2;else if(!strcmp(event,"offline"))message.kind=3;}
  cJSON_Delete(root);if(!message.kind)return false;
 }
 *out=message;return true;
}
