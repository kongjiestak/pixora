#pragma once
#include <stdbool.h>
#include <string.h>
typedef struct {char ssid[33],password[65];} wifi_saved_credentials;
static inline bool wifi_credentials_valid(const char *ssid,const char *password,bool secure){
 if(!ssid||!password||!ssid[0]||strlen(ssid)>32)return false;
 size_t length=strlen(password);
 if(!secure)return length==0;
 if(length==64){for(size_t i=0;i<64;i++)if(!((password[i]>='0'&&password[i]<='9')||(password[i]>='a'&&password[i]<='f')||(password[i]>='A'&&password[i]<='F')))return false;return true;}
 if(length<8||length>63)return false;
 for(size_t i=0;i<length;i++)if((unsigned char)password[i]<32||(unsigned char)password[i]>126)return false;
 return true;
}
