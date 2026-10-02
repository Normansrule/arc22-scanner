// Keep standard/ESP-IDF headers ABOVE ArduCAM.h (it defines a `swap` macro on
// some platforms; tools/fetch_libraries.py also neutralises it in the vendored copy).
#include "camera.h"

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <string.h>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "pins.h"
#include "sdkconfig.h"

#include "ArduCAM.h"  // last on purpose
#undef swap

static const char *TAG = "camera";
static constexpr uint8_t kChipIdHigh = 0x0A;  // OV2640 sensor bank, from ov2640_regs.h
static constexpr uint8_t kChipIdLow = 0x0B;
// Constructed in camera_begin() (its constructor touches GPIO), not at static-init time.
static ArduCAM *s_cam = nullptr;
#define cam (*s_cam)

CamStatus camera_begin() {
    CamStatus st;
    if (!s_cam) s_cam = new ArduCAM(OV2640, PIN_CAM_CS);
    Wire.begin(PIN_CAM_SDA, PIN_CAM_SCL, 100000);
    // Arduino global SPI = SPI2/FSPI; the display uses SPI3 through LovyanGFX.
    SPI.begin(PIN_CAM_SCLK, PIN_CAM_MISO, PIN_CAM_MOSI, PIN_CAM_CS);
    SPI.setFrequency(CONFIG_ARC_CAMERA_SPI_HZ);
    pinMode(PIN_CAM_CS, OUTPUT);
    digitalWrite(PIN_CAM_CS, HIGH);

    // reset the ArduChip CPLD
    cam.write_reg(0x07, 0x80);
    delay(100);
    cam.write_reg(0x07, 0x00);
    delay(100);

    for (int i = 0; i < 5 && !st.spi_ok; i++) {
        cam.write_reg(ARDUCHIP_TEST1, 0x55);
        st.spi_ok = cam.read_reg(ARDUCHIP_TEST1) == 0x55;
        if (!st.spi_ok) delay(200);
    }
    if (!st.spi_ok) {
        ESP_LOGE(TAG, "SPI test failed: check CS/MOSI/MISO/SCLK wiring, CS pull-up, camera VCC");
        return st;
    }
    cam.wrSensorReg8_8(0xff, 0x01);
    cam.rdSensorReg8_8(kChipIdHigh, &st.vid);
    cam.rdSensorReg8_8(kChipIdLow, &st.pid);
    st.sensor_ok = (st.vid == 0x26) && (st.pid == 0x41 || st.pid == 0x42);
    if (!st.sensor_ok) {
        ESP_LOGE(TAG, "OV2640 not found on I2C (vid=0x%02x pid=0x%02x): check SDA/SCL", st.vid, st.pid);
        return st;
    }
    cam.set_format(JPEG);
    cam.InitCAM();
    cam.OV2640_set_JPEG_size(OV2640_320x240);
#if CONFIG_ARC_CAM_FLIP_180
    // OV2640 REG04 (sensor bank): bit7 HFLIP, bit6 VFLIP. VERIFY on your module.
    uint8_t r04 = 0;
    cam.wrSensorReg8_8(0xff, 0x01);
    cam.rdSensorReg8_8(0x04, &r04);
    cam.wrSensorReg8_8(0x04, r04 | 0xC0);
#endif
    delay(500);  // let auto-exposure settle
    cam.clear_fifo_flag();
    ESP_LOGI(TAG, "OV2640 ready (JPEG 320x240, SPI %d Hz)", CONFIG_ARC_CAMERA_SPI_HZ);
    return st;
}

bool camera_capture_jpeg(uint8_t **out, size_t *out_len, uint32_t timeout_ms) {
    *out = nullptr;
    *out_len = 0;
    if (!s_cam) return false;
    cam.flush_fifo();
    cam.clear_fifo_flag();
    cam.start_capture();
    uint32_t t0 = millis();
    while (!cam.get_bit(ARDUCHIP_TRIG, CAP_DONE_MASK)) {
        if (millis() - t0 > timeout_ms) {
            ESP_LOGE(TAG, "capture timeout");
            return false;
        }
        delay(2);
    }
    uint32_t len = cam.read_fifo_length();
    if (len == 0 || len >= MAX_FIFO_SIZE) {
        ESP_LOGE(TAG, "bad FIFO length %u", (unsigned)len);
        return false;
    }
    uint8_t *buf = (uint8_t *)heap_caps_malloc(len + 8, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGE(TAG, "no PSRAM for %u bytes", (unsigned)len);
        return false;
    }
    cam.CS_LOW();
    cam.set_fifo_burst();
    for (uint32_t i = 0; i < len; i++) buf[i] = SPI.transfer(0x00);
    cam.CS_HIGH();
    cam.clear_fifo_flag();

    // Trim to SOI (FFD8) .. EOI (FFD9): some modules prepend a dummy byte.
    size_t s = 0, e = 0;
    for (size_t i = 0; i + 1 < len; i++) {
        if (buf[i] == 0xFF && buf[i + 1] == 0xD8) { s = i; break; }
    }
    for (size_t i = len - 1; i > s; i--) {
        if (buf[i - 1] == 0xFF && buf[i] == 0xD9) { e = i + 1; break; }
    }
    if (e <= s + 4) {
        ESP_LOGE(TAG, "no JPEG markers in %u bytes", (unsigned)len);
        heap_caps_free(buf);
        return false;
    }
    if (s) memmove(buf, buf + s, e - s);
    *out = buf;
    *out_len = e - s;
    return true;
}
