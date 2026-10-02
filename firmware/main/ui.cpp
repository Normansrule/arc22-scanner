#include "ui.h"

#include <algorithm>

#include <Arduino.h>

#include "coco_labels.h"
#include "display.h"

namespace ui {

static const uint16_t CYAN = 0x2E7F;   // ARC-22 accent (approx. #2dcffd)
static const uint16_t PANEL = 0x10A2;  // dark blue-grey
static const uint16_t BOX_COL[8] = {0x2E7F, 0xFFE0, 0xF81F, 0x07E0, 0xFD20, 0x7BEF, 0xF800, 0x001F};

void header(const char *title) {
    lcd.fillRect(0, 0, W, 28, PANEL);
    lcd.setFont(&fonts::FreeSansBold9pt7b);
    lcd.setTextColor(CYAN, PANEL);
    lcd.setTextDatum(textdatum_t::middle_left);
    lcd.drawString(title, 8, 14);
}

void buttons(const char *a, const char *b, const char *c, bool b_enabled, bool c_enabled) {
    const char *lab[3] = {a, b, c};
    bool en[3] = {true, b_enabled, c_enabled};
    lcd.setFont(&fonts::FreeSansBold12pt7b);
    lcd.setTextDatum(textdatum_t::middle_center);
    for (int i = 0; i < 3; i++) {
        int x = i * (W / 3) + 3, w = W / 3 - 6;
        uint16_t bg = (lab[i] && en[i]) ? CYAN : PANEL;
        lcd.fillRoundRect(x, BTN_Y, w, BTN_H, 10, bg);
        if (lab[i]) {
            lcd.setTextColor(en[i] ? TFT_BLACK : 0x7BEF, bg);
            lcd.drawString(lab[i], x + w / 2, BTN_Y + BTN_H / 2);
        }
    }
}

int hit_button(int x, int y) {
    if (y < BTN_Y || y > BTN_Y + BTN_H) return -1;
    return constrain(x / (W / 3), 0, 2);
}

void status(const char *text, uint16_t color) {
    lcd.fillRect(0, IMG_H + 2, W, 22, TFT_BLACK);
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.setTextColor(color, TFT_BLACK);
    lcd.setTextDatum(textdatum_t::middle_left);
    lcd.drawString(text, 6, IMG_H + 13);
}

void image(const uint8_t *jpeg, size_t len) { lcd.drawJpg(jpeg, len, 0, 0, W, IMG_H); }

void boxes(const DetectResult &r, int selected) {
    lcd.setFont(&fonts::Font2);
    lcd.setTextDatum(textdatum_t::bottom_left);
    for (int i = 0; i < r.count; i++) {
        const Detection &d = r.det[i];
        uint16_t c = BOX_COL[i % 8];
        int w = d.x2 - d.x1, h = d.y2 - d.y1;
        lcd.drawRect(d.x1, d.y1, w, h, c);
        if (i == selected) {
            lcd.drawRect(d.x1 + 1, d.y1 + 1, w - 2, h - 2, c);
            lcd.drawRect(d.x1 + 2, d.y1 + 2, w - 4, h - 4, c);
        }
        lcd.setTextColor(TFT_BLACK, c);
        char s[40];
        snprintf(s, sizeof s, " %d %s ", i + 1, coco_label(d.category).name);
        lcd.drawString(s, d.x1, std::max(d.y1, 14));
    }
}

void result_list(const DetectResult &r, int selected) {
    lcd.fillRect(0, IMG_H + 26, W, BTN_Y - IMG_H - 30, TFT_BLACK);
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.setTextDatum(textdatum_t::middle_left);
    if (r.count == 0) {
        lcd.setTextColor(0xBDF7, TFT_BLACK);
        lcd.drawString("No COCO object found. Try closer / more light.", 6, IMG_H + 40);
        return;
    }
    for (int i = 0; i < r.count; i++) {
        int y = IMG_H + 28 + i * 18;
        bool sel = (i == selected);
        if (sel) lcd.fillRect(0, y, W, 18, PANEL);
        lcd.setTextColor(BOX_COL[i % 8], sel ? PANEL : TFT_BLACK);
        char s[64];
        snprintf(s, sizeof s, "%d  %-14s %3d%%", i + 1, coco_label(r.det[i].category).name,
                 (int)(r.det[i].score * 100 + 0.5f));
        lcd.drawString(s, 6, y + 9);
    }
}

int hit_detection(const DetectResult &r, int x, int y) {
    if (y >= IMG_H + 28 && y < IMG_H + 28 + r.count * 18) return (y - IMG_H - 28) / 18;
    int best = -1, best_area = 1 << 30;  // smallest box containing the tap wins
    for (int i = 0; i < r.count; i++) {
        const Detection &d = r.det[i];
        if (x >= d.x1 && x <= d.x2 && y >= d.y1 && y <= d.y2) {
            int a = (d.x2 - d.x1) * (d.y2 - d.y1);
            if (a < best_area) best = i, best_area = a;
        }
    }
    return best;
}

void article(const WikiResult &w, int coco_index) {
    lcd.fillScreen(TFT_BLACK);
    header(w.title.empty() ? coco_label(coco_index).wiki : w.title.c_str());
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.setTextColor(TFT_WHITE, TFT_BLACK);
    lcd.setClipRect(6, 34, W - 12, BTN_Y - 40);
    lcd.setTextWrap(true, false);
    lcd.setCursor(6, 36);
    lcd.print(w.extract.c_str());
    lcd.clearClipRect();
    lcd.setFont(&fonts::Font0);
    lcd.setTextColor(0x7BEF, TFT_BLACK);
    lcd.setTextDatum(textdatum_t::bottom_left);
    lcd.drawString(w.from_cache ? "Wikipedia (cached), CC BY-SA" : "Wikipedia, CC BY-SA", 6, BTN_Y - 4);
    buttons("BACK", "QR", "GOOGLE");
}

void qr(const std::string &url, const char *caption) {
    lcd.fillScreen(TFT_WHITE);
    lcd.qrcode(url.c_str(), 30, 60, 260, 6);
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.setTextColor(TFT_BLACK, TFT_WHITE);
    lcd.setTextDatum(textdatum_t::middle_center);
    lcd.drawString(caption, W / 2, 30);
    lcd.setFont(&fonts::Font0);
    lcd.drawString(url.c_str(), W / 2, 340);
    buttons("BACK", nullptr, nullptr, false, false);
}

bool wait_touch(int *x, int *y, uint32_t timeout_ms) {
    uint32_t t0 = millis();
    int32_t tx, ty;
    while (lcd.getTouch(&tx, &ty)) {  // wait for release of any previous touch
        if (millis() - t0 > timeout_ms) return false;
        delay(10);
    }
    while (millis() - t0 < timeout_ms) {
        if (lcd.getTouch(&tx, &ty)) {
            *x = tx;
            *y = ty;
            return true;
        }
        delay(10);
    }
    return false;
}

}  // namespace ui
