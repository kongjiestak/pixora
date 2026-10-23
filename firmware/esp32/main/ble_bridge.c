#include "ble_bridge.h"
#include "ble_wire.h"
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
static const ble_uuid128_t service_uuid=BLE_UUID128_INIT(1,0xb6,0xb6,0x36,0xed,0x2d,0xb6,0x9d,0x58,0x4d,0xf2,0x40,0xe0,0x4d,0x4b,0x36);
static const ble_uuid128_t hello_uuid=BLE_UUID128_INIT(2,0xb6,0xb6,0x36,0xed,0x2d,0xb6,0x9d,0x58,0x4d,0xf2,0x40,0xe0,0x4d,0x4b,0x36);
static const ble_uuid128_t data_uuid=BLE_UUID128_INIT(3,0xb6,0xb6,0x36,0xed,0x2d,0xb6,0x9d,0x58,0x4d,0xf2,0x40,0xe0,0x4d,0x4b,0x36);
static const ble_uuid128_t ack_uuid=BLE_UUID128_INIT(4,0xb6,0xb6,0x36,0xed,0x2d,0xb6,0x9d,0x58,0x4d,0xf2,0x40,0xe0,0x4d,0x4b,0x36);
static atomic_bool enabled;
static bool synced,initialized;
static uint8_t own_address;
static uint16_t connection=BLE_HS_CONN_HANDLE_NONE;
static const char *token;
static char nonce[33],hello[128],ack[160];
static uint32_t sequence;
static int64_t started;
static ble_wire_buffer *buffer;
static uint8_t *plaintext;
static usb_message *incoming;
static QueueHandle_t messages;
static struct ble_npl_event control;
static void advertise(void);
static void clear_session(void){
    ble_wire_reset(buffer);memset(plaintext,0,BLE_WIRE_MAX_PLAIN+1);
    memset(nonce,0,sizeof(nonce));memset(hello,0,sizeof(hello));memset(ack,0,sizeof(ack));
    sequence=0;started=0;xQueueReset(messages);
}
static int gap_event(struct ble_gap_event *event,void *arg){
    (void)arg;
    if(event->type==BLE_GAP_EVENT_CONNECT){
        if(event->connect.status){advertise();return 0;}
        connection=event->connect.conn_handle;clear_session();
        if(!atomic_load(&enabled)){ble_gap_terminate(connection,BLE_ERR_REM_USER_CONN_TERM);return 0;}
        for(int i=0;i<16;i++)snprintf(nonce+i*2,3,"%02x",(unsigned)(esp_random()&255));
        char message[40],proof[65];snprintf(message,sizeof(message),"hello %s",nonce);
        if(!usb_digest(token,message,strlen(message),proof))return BLE_HS_EAPP;
        snprintf(hello,sizeof(hello),"PXUSB_HELLO %s %s\n",nonce,proof);
    }else if(event->type==BLE_GAP_EVENT_DISCONNECT){
        connection=BLE_HS_CONN_HANDLE_NONE;clear_session();advertise();
    }else if(event->type==BLE_GAP_EVENT_ADV_COMPLETE)advertise();
    return 0;
}
static void advertise(void){
    if(!synced||!atomic_load(&enabled)||connection!=BLE_HS_CONN_HANDLE_NONE||ble_gap_adv_active())return;
    struct ble_hs_adv_fields fields={0};
    fields.flags=BLE_HS_ADV_F_DISC_GEN|BLE_HS_ADV_F_BREDR_UNSUP;
    fields.uuids128=(ble_uuid128_t*)&service_uuid;fields.num_uuids128=1;fields.uuids128_is_complete=1;
    if(ble_gap_adv_set_fields(&fields))return;
    struct ble_hs_adv_fields response={0};
    response.name=(uint8_t*)"Pixora";response.name_len=6;response.name_is_complete=1;
    if(ble_gap_adv_rsp_set_fields(&response))return;
    struct ble_gap_adv_params params={0};params.conn_mode=BLE_GAP_CONN_MODE_UND;params.disc_mode=BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(own_address,NULL,BLE_HS_FOREVER,&params,gap_event,NULL);
}
static void control_event(struct ble_npl_event *event){
    (void)event;
    if(!atomic_load(&enabled)){
        ble_gap_adv_stop();
        if(connection!=BLE_HS_CONN_HANDLE_NONE)ble_gap_terminate(connection,BLE_ERR_REM_USER_CONN_TERM);
        clear_session();
    }else advertise();
}
static int access_data(uint16_t conn,uint16_t attribute,struct ble_gatt_access_ctxt *ctx,void *arg){
    (void)attribute;
    if(!atomic_load(&enabled)||conn!=connection||!nonce[0])return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
    unsigned which=(unsigned)(uintptr_t)arg;
    if(ctx->op==BLE_GATT_ACCESS_OP_READ_CHR){
        const char *value=which==1?hello:which==3?ack:"";
        return os_mbuf_append(ctx->om,value,strlen(value))?BLE_ATT_ERR_INSUFFICIENT_RES:0;
    }
    if(which!=2||ctx->op!=BLE_GATT_ACCESS_OP_WRITE_CHR)return BLE_ATT_ERR_UNLIKELY;
    size_t size=OS_MBUF_PKTLEN(ctx->om);uint8_t chunk[512];
    if(!size||size>sizeof(chunk))return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
    if(os_mbuf_copydata(ctx->om,0,size,chunk))return BLE_ATT_ERR_UNLIKELY;
    int64_t now=esp_timer_get_time();
    if(started&&now-started>10000000){ble_wire_reset(buffer);started=0;return BLE_ATT_ERR_UNLIKELY;}
    if(!started)started=now;
    int result=ble_wire_feed(buffer,chunk,size);
    if(result<0){ble_gap_terminate(conn,BLE_ERR_REM_USER_CONN_TERM);return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;}
    if(!result)return 0;
    size_t written=0;
    bool valid=ble_wire_open(buffer,token,plaintext,BLE_WIRE_MAX_PLAIN,&written);
    if(valid){
        /* USB parser expects no terminal newline. */
        if(written&&plaintext[written-1]=='\n')written--;
        valid=usb_frame_parse((const char*)plaintext,written,token,nonce,incoming)&&incoming->sequence>sequence;
    }
    memset(plaintext,0,BLE_WIRE_MAX_PLAIN+1);ble_wire_reset(buffer);started=0;
    if(!valid){ble_gap_terminate(conn,BLE_ERR_REM_USER_CONN_TERM);return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;}
    sequence=incoming->sequence;
    if(xQueueOverwrite(messages,incoming)!=pdPASS)return BLE_ATT_ERR_INSUFFICIENT_RES;
    const char *kind=incoming->kind==1?"data":incoming->kind==2?"revoked":"offline";
    char message[100],proof[65];snprintf(message,sizeof(message),"ack %s %" PRIu32 " %s",nonce,sequence,kind);
    if(!usb_digest(token,message,strlen(message),proof))return BLE_ATT_ERR_UNLIKELY;
    snprintf(ack,sizeof(ack),"PXBLE_ACK %" PRIu32 " %s %s",sequence,kind,proof);
    return 0;
}
static const struct ble_gatt_svc_def services[]={
    {.type=BLE_GATT_SVC_TYPE_PRIMARY,.uuid=&service_uuid.u,.characteristics=(struct ble_gatt_chr_def[]){
        {.uuid=&hello_uuid.u,.access_cb=access_data,.arg=(void*)1,.flags=BLE_GATT_CHR_F_READ},
        {.uuid=&data_uuid.u,.access_cb=access_data,.arg=(void*)2,.flags=BLE_GATT_CHR_F_WRITE},
        {.uuid=&ack_uuid.u,.access_cb=access_data,.arg=(void*)3,.flags=BLE_GATT_CHR_F_READ},
        {0}}},{0}};
static void on_sync(void){if(!ble_hs_util_ensure_addr(0)&&!ble_hs_id_infer_auto(0,&own_address)){synced=true;advertise();}}
static void host_task(void *arg){(void)arg;nimble_port_run();nimble_port_freertos_deinit();}
esp_err_t ble_bridge_init(const char *scoped_token){
    if(initialized||!scoped_token||!scoped_token[0])return ESP_ERR_INVALID_STATE;
    token=scoped_token;
    buffer=heap_caps_calloc(1,sizeof(*buffer),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    plaintext=heap_caps_calloc(1,BLE_WIRE_MAX_PLAIN+1,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    incoming=heap_caps_calloc(1,sizeof(*incoming),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    messages=xQueueCreate(1,sizeof(usb_message));
    if(!buffer||!plaintext||!incoming||!messages)return ESP_ERR_NO_MEM;
    esp_err_t result=nimble_port_init();if(result!=ESP_OK)return result;
    ble_hs_cfg.sync_cb=on_sync;ble_svc_gap_init();ble_svc_gatt_init();
    ble_svc_gap_device_name_set("Pixora");
    if(ble_gatts_count_cfg(services)||ble_gatts_add_svcs(services))return ESP_FAIL;
    ble_npl_event_init(&control,control_event,NULL);initialized=true;
    nimble_port_freertos_init(host_task);return ESP_OK;
}
void ble_bridge_enable(bool on){
    atomic_store(&enabled,on);
    if(initialized)ble_npl_eventq_put(nimble_port_get_dflt_eventq(),&control);
}
bool ble_bridge_receive(usb_message *message){return initialized&&atomic_load(&enabled)&&xQueueReceive(messages,message,0)==pdTRUE;}
