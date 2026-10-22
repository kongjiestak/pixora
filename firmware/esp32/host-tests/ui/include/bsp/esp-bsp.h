#pragma once
#include "lvgl.h"
#include "nvs.h"
esp_err_t bsp_display_brightness_set(int);
lv_indev_t *bsp_display_get_input_dev(void);
