// ARC-22 FitFirst scanner — firmware entry point.
//
// Stage 4 (default build): COMMISSION_CAPTURE_ONLY — display, touch calibration,
//   camera image and orientation. No model is loaded.
// Stage 5: set CONFIG_ARC_COMMISSION_CAPTURE_ONLY=n → point, tap SCAN, a still is
//   captured and object detection runs ON the ESP32-S3; tap a box, tap LEARN for a
//   Wikipedia intro (cached, with QR / Google fallbacks). Wi-Fi is used for the
//   article lookup only and is switched off before every detection.
//
// Latency: Espressif lists ~6.2 s for the model alone on an ESP32-S3; the full
// capture → decode → detect → draw path on this device is slower and UNMEASURED.
// This is a still-photo scanner, not live video recognition.

#include <Arduino.h>

#include "camera.h"
#include "coco_labels.h"
#include "detector.h"
#include "display.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "ui.h"
#include "wiki.h"

static const char *TAG = "arc22";

static void free_jpeg(uint8_t *&p) {
    if (p) heap_caps_free(p);
    p = nullptr;
}

// --------------------------------------------------------------------------
// Stage 4 — commissioning
// --------------------------------------------------------------------------
#if CONFIG_ARC_COMMISSION_CAPTURE_ONLY
static void page_display() {
    lcd.fillScreen(TFT_BLACK);
    ui::header("1/3 DISPLAY + ORIENTATION");
    const uint16_t bars[] = {TFT_WHITE, TFT_YELLOW, TFT_CYAN, TFT_GREEN, TFT_MAGENTA, TFT_RED, TFT_BLUE, TFT_BLACK};
    for (int i = 0; i < 8; i++) lcd.fillRect(i * 40, 40, 40, 120, bars[i]);
    lcd.fillTriangle(160, 180, 120, 240, 200, 240, 0x2E7F);
    lcd.fillRect(150, 240, 20, 50, 0x2E7F);
    lcd.setFont(&fonts::FreeSans9pt7b);
    lcd.setTextColor(TFT_WHITE, TFT_BLACK);
    lcd.setTextDatum(textdatum_t::middle_center);
    lcd.drawString("Arrow must point to the TOP of the scanner.", 160, 310);
    lcd.drawString("Bars: white yellow cyan green magenta red blue.", 160, 335);
    lcd.drawString("Wrong? change ARC_LCD_ROTATION / invert / rgb_order.", 160, 360);
    ui::buttons("RECAL", "NEXT", nullptr, true, false);
}

static void page_touch() {
    lcd.fillScreen(TFT_BLACK);
    ui::header("2/3 TOUCH - draw anywhere");
    ui::buttons("CLEAR", "NEXT", nullptr, true, false);
}

static void run_commission(const CamStatus &cs) {
    int page = 0, x, y;
    page_display();
    while (page == 0) {
        if (!ui::wait_touch(&x, &y, 60000)) continue;
        int b = ui::hit_button(x, y);
        if (b == 0) {
            display_begin(true);
            page_display();
        } else if (b == 1) {
            page = 1;
        }
    }
    page_touch();
    while (page == 1) {
        int32_t tx, ty;
        if (lcd.getTouch(&tx, &ty)) {
            int b = ui::hit_button(tx, ty);
            if (b == 0) {
                page_touch();
                delay(250);
            } else if (b == 1) {
                page = 2;
            } else if (ty < ui::BTN_Y - 4) {
                lcd.fillCircle(tx, ty, 3, 0x2E7F);
                char s[32];
                snprintf(s, sizeof s, "x=%3ld y=%3ld", (long)tx, (long)ty);
                lcd.setFont(&fonts::Font2);
                lcd.setTextColor(TFT_WHITE, TFT_BLACK);
                lcd.setTextDatum(textdatum_t::top_left);
                lcd.drawString(s, 8, 34);
            }
        }
        delay(5);
    }
    lcd.fillScreen(TFT_BLACK);
    char s[96];
    snprintf(s, sizeof s, "3/3 CAMERA  SPI %s  I2C %s (%02X/%02X)", cs.spi_ok ? "OK" : "FAIL",
             cs.sensor_ok ? "OK" : "FAIL", cs.vid, cs.pid);
    ESP_LOGI(TAG, "%s", s);
    bool frozen = false;
    uint32_t frames = 0, t0 = millis();
    ui::buttons("FREEZE", "RECAL", nullptr, true, false);
    while (true) {
        if (cs.spi_ok && cs.sensor_ok && !frozen) {
            uint8_t *jpg = nullptr;
            size_t len = 0;
            if (camera_capture_jpeg(&jpg, &len)) {
                ui::image(jpg, len);
                frames++;
                char st[80];
                snprintf(st, sizeof st, "JPEG %u B  %.1f fps  PSRAM free %u k", (unsigned)len,
                         frames * 1000.0f / (millis() - t0 + 1), (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024));
                ui::status(st);
            } else {
                ui::status("capture failed - see serial log", TFT_RED);
            }
            free_jpeg(jpg);
        } else if (!(cs.spi_ok && cs.sensor_ok)) {
            ui::status(s, TFT_RED);
            delay(500);
        }
        lcd.setFont(&fonts::FreeSans9pt7b);
        lcd.setTextColor(TFT_WHITE, TFT_BLACK);
        lcd.setTextDatum(textdatum_t::middle_left);
        lcd.drawString("Image upright? Same way round as the scene?", 6, 290);
        lcd.drawString("If flipped: ARC_CAM_FLIP_180 / ARC_LCD_ROTATION.", 6, 312);
        lcd.drawString("All good -> set ARC_COMMISSION_CAPTURE_ONLY=n", 6, 350);
        lcd.drawString("in menuconfig, rebuild, flash (stage 5).", 6, 372);
        int32_t tx, ty;
        if (lcd.getTouch(&tx, &ty)) {
            int b = ui::hit_button(tx, ty);
            if (b == 0) {
                frozen = !frozen;
                ui::buttons(frozen ? "LIVE" : "FREEZE", "RECAL", nullptr, true, false);
            } else if (b == 1) {
                display_begin(true);
                lcd.fillScreen(TFT_BLACK);
                ui::buttons("FREEZE", "RECAL", nullptr, true, false);
            }
            delay(300);
        }
    }
}
#endif

// --------------------------------------------------------------------------
// Stage 5 — scanner
// --------------------------------------------------------------------------
#if !CONFIG_ARC_COMMISSION_CAPTURE_ONLY
static bool s_dim = false;

static void idle_screen() {
    lcd.fillScreen(TFT_BLACK);
    ui::status("Aim the front camera, then tap SCAN", 0x2E7F);
    ui::buttons("SCAN", "LEARN", "DIM", false, display_has_backlight_control());
}

static void show_article_flow(int cat) {
    ui::status("Looking up (Wi-Fi on for this only)...", TFT_YELLOW);
    WikiResult w = wiki_lookup(cat);
    int x, y;
    if (!w.ok) {
        ui::qr(wiki_url(cat), (std::string("Offline: ") + w.error).c_str());
    } else {
        ui::article(w, cat);
    }
    while (true) {
        if (!ui::wait_touch(&x, &y, 120000)) return;
        int b = ui::hit_button(x, y);
        if (b == 0) return;
        if (b == 1) ui::qr(wiki_url(cat), "Wikipedia");
        if (b == 2) ui::qr(google_url(cat), "Google search");
    }
}

static void run_scanner() {
    idle_screen();
    DetectResult last;
    int selected = -1;
    uint8_t *still = nullptr;
    size_t still_len = 0;
    const float thr = CONFIG_ARC_SCORE_THRESHOLD_PCT / 100.0f;
    while (true) {
        // live aiming preview until SCAN
        if (!still) {
            uint8_t *jpg = nullptr;
            size_t len = 0;
            if (camera_capture_jpeg(&jpg, &len, 1500)) ui::image(jpg, len);
            free_jpeg(jpg);
        }
        int32_t tx, ty;
        if (!lcd.getTouch(&tx, &ty)) {
            delay(5);
            continue;
        }
        int b = ui::hit_button(tx, ty);
        if (b == 0) {  // SCAN (or NEW after a scan)
            free_jpeg(still);
            selected = -1;
            if (!camera_capture_jpeg(&still, &still_len)) {
                ui::status("Capture failed - check camera wiring", TFT_RED);
                continue;
            }
            ui::image(still, still_len);
            ui::status("Detecting on-device... (several seconds)", TFT_YELLOW);
            ui::buttons("...", "LEARN", "DIM", false, display_has_backlight_control());
            wifi_off();  // never run inference with the radio up
            last = detector_run(still, still_len, thr, CONFIG_ARC_MAX_DETECTIONS);
            ui::image(still, still_len);
            ui::boxes(last, selected);
            ui::result_list(last, selected);
            char st[64];
            snprintf(st, sizeof st, "%d found  decode %u ms  detect %u ms", last.count, (unsigned)last.decode_ms,
                     (unsigned)last.infer_ms);
            ui::status(last.ok ? st : "Detection failed - see serial log", last.ok ? 0x2E7F : TFT_RED);
            ui::buttons("NEW", "LEARN", "DIM", false, display_has_backlight_control());
        } else if (b == 1 && still && selected >= 0) {  // LEARN
            show_article_flow(last.det[selected].category);
            lcd.fillScreen(TFT_BLACK);
            ui::image(still, still_len);
            ui::boxes(last, selected);
            ui::result_list(last, selected);
            ui::buttons("NEW", "LEARN", "DIM", true, display_has_backlight_control());
        } else if (b == 2 && display_has_backlight_control()) {  // DIM
            s_dim = !s_dim;
            display_set_dim(s_dim);
        } else if (still && ty < ui::BTN_Y) {  // select a box or list row
            int hit = ui::hit_detection(last, tx, ty);
            if (hit >= 0) {
                selected = hit;
                ui::image(still, still_len);
                ui::boxes(last, selected);
                ui::result_list(last, selected);
                char st[64];
                snprintf(st, sizeof st, "Selected: %s - tap LEARN", coco_label(last.det[hit].category).name);
                ui::status(st, 0x2E7F);
                ui::buttons("NEW", "LEARN", "DIM", true, display_has_backlight_control());
            }
        }
        while (lcd.getTouch(&tx, &ty)) delay(10);  // debounce: wait for release
    }
}
#endif

extern "C" void app_main(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    initArduino();
    ESP_LOGI(TAG, "ARC-22 FitFirst firmware, PSRAM %u KB free",
             (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024));
    display_begin(false);
    CamStatus cs = camera_begin();
#if CONFIG_ARC_COMMISSION_CAPTURE_ONLY
    run_commission(cs);
#else
    if (!(cs.spi_ok && cs.sensor_ok)) {
        ui::status("Camera not found - rebuild in commissioning mode", TFT_RED);
    }
    wifi_off();
    run_scanner();
#endif
}
