/* Keep UI allocations in PSRAM; internal DMA-capable memory belongs to drivers/tasks. */
#include "lvgl.h"
#include "ui_memory.h"
#include <assert.h>
#include "esp_heap_caps.h"
#include <string.h>
void pixora_ui_memory_prepare(void){assert(heap_caps_get_total_size(MALLOC_CAP_SPIRAM)>0);}
#if LV_USE_STDLIB_MALLOC == LV_STDLIB_CUSTOM
void lv_mem_init(void){}
void lv_mem_deinit(void){}
lv_mem_pool_t lv_mem_add_pool(void *memory,size_t bytes){(void)memory;(void)bytes;return NULL;}
void lv_mem_remove_pool(lv_mem_pool_t pool){(void)pool;}
void *lv_malloc_core(size_t bytes){return heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);}
void *lv_realloc_core(void *memory,size_t bytes){return heap_caps_realloc(memory,bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);}
void lv_free_core(void *memory){heap_caps_free(memory);}
void lv_mem_monitor_core(lv_mem_monitor_t *report){
 memset(report,0,sizeof(*report));report->total_size=heap_caps_get_total_size(MALLOC_CAP_SPIRAM);report->free_size=heap_caps_get_free_size(MALLOC_CAP_SPIRAM);report->free_biggest_size=heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);
 if(report->total_size)report->used_pct=100-report->free_size*100/report->total_size;
 if(report->free_size)report->frag_pct=100-report->free_biggest_size*100/report->free_size;
}
lv_result_t lv_mem_test_core(void){return heap_caps_check_integrity(MALLOC_CAP_SPIRAM,false)?LV_RESULT_OK:LV_RESULT_INVALID;}
#endif
