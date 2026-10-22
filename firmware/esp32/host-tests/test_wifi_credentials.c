#include <assert.h>
#include <stdio.h>
#include "wifi_credentials.h"
int main(void){
 assert(wifi_credentials_valid("Home","password",true));
 assert(wifi_credentials_valid("家庭Wi-Fi","password",true));
 assert(wifi_credentials_valid("Open","",false));
 assert(!wifi_credentials_valid("Open","password",false));
 assert(!wifi_credentials_valid("Home","short",true));
 assert(!wifi_credentials_valid("Home","bad\npass",true));
 assert(!wifi_credentials_valid("","password",true));
 assert(!wifi_credentials_valid("123456789012345678901234567890123","password",true));
 assert(wifi_credentials_valid("Home","0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",true));
 assert(!wifi_credentials_valid("Home","z123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",true));
 puts("Wi-Fi credential length/security boundary tests passed");
}
