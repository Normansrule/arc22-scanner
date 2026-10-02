#include "display.h"

#include "esp_log.h"
#include "nvs.h"

static const char *TAG = "display";
LGFX lcd;

static bool load_cal(uint16_t cal[8]) {
    nvs_handle_t h;
    if (nvs_open("arc22", NVS_READONLY, &h) != ESP_OK) return false;
    size_t len = sizeof(uint16_t) * 8;
    esp_err_t err = nvs_get_blob(h, "touch_cal", cal, &len);
    nvs_close(h);
    return err == ESP_OK && len == sizeof(uint16_t) * 8;
}

static void save_cal(const uint16_t cal[8]) {
    nvs_handle_t h;
    if (nvs_open("arc22", NVS_READWRITE, &h) != ESP_OK) return;
    nvs_set_blob(h, "touch_cal", cal, sizeof(uint16_t) * 8);
    nvs_commit(h);
    nvs_close(h);
}

void display_begin(bool force_calibration) {
    lcd.init();
    lcd.setRotation(CONFIG_ARC_LCD_ROTATION);
    lcd.setBrightness(255);
    lcd.fillScreen(TFT_BLACK);
    uint16_t cal[8];
    if (!force_calibration && load_cal(cal)) {
        lcd.setTouchCalibrate(cal);
        ESP_LOGI(TAG, "touch calibration loaded from NVS");
        return;
    }
    lcd.setTextColor(TFT_WHITE, TFT_BLACK);
    lcd.setTextDatum(textdatum_t::middle_center);
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.drawString("Touch calibration", lcd.width() / 2, lcd.height() / 2 - 20);
    lcd.drawString("tap each arrow tip with a stylus", lcd.width() / 2, lcd.height() / 2 + 6);
    lcd.calibrateTouch(cal, TFT_CYAN, TFT_BLACK, 16);
    save_cal(cal);
    ESP_LOGI(TAG, "touch calibration stored");
    lcd.fillScreen(TFT_BLACK);
}

bool display_has_backlight_control() {
#if CONFIG_ARC_BACKLIGHT_GPIO_ENABLED
    return true;
#else
    return false;
#endif
}

void display_set_dim(bool dim) {
#if CONFIG_ARC_BACKLIGHT_GPIO_ENABLED
    lcd.setBrightness(dim ? 50 : 255);
#else
    (void)dim;
#endif
}
