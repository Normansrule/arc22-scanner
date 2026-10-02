// Screen layout helpers (portrait 320 x 480; image area 320 x 240 at the top).
#pragma once
#include <stddef.h>
#include <stdint.h>

#include <string>

#include "detector.h"
#include "wiki.h"

namespace ui {
constexpr int W = 320, H = 480;
constexpr int IMG_H = 240;
constexpr int BTN_Y = 414, BTN_H = 60;

void buttons(const char *a, const char *b, const char *c, bool b_enabled = true, bool c_enabled = true);
int hit_button(int x, int y);  // 0..2 or -1
void status(const char *text, uint16_t color = 0xFFFF);
void image(const uint8_t *jpeg, size_t len);
void boxes(const DetectResult &r, int selected);
void result_list(const DetectResult &r, int selected);
int hit_detection(const DetectResult &r, int x, int y);  // index or -1
void article(const WikiResult &w, int coco_index);
void qr(const std::string &url, const char *caption);
void header(const char *title);
bool wait_touch(int *x, int *y, uint32_t timeout_ms);  // true on a new tap (debounced)
}  // namespace ui
