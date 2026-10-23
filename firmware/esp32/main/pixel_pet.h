#pragma once
#include "lvgl.h"
#define PIXORA_PET_WIDTH 192
#define PIXORA_PET_HEIGHT 224
/* Original code-drawn Pixora companion, not an exported Codex asset. */
void pixel_pet_draw(lv_draw_buf_t *buffer,unsigned state,unsigned pose,bool greeting,uint32_t accent);
