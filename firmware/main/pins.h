// ARC-22 pin map — the ONLY place pins are defined. Mirrors docs/WIRING.md.
// All GPIO logic is 3.3 V. Never connect a 5 V signal to any of these pins.
// VERIFY every number against the silkscreen of YOUR ESP32-S3 board before wiring.
#pragma once

// ---- Camera: Arducam Mini / Mini Plus OV2640 (needs BOTH SPI and I2C) --------
#define PIN_CAM_SDA 4    // I2C data  (sensor registers)
#define PIN_CAM_SCL 5    // I2C clock
#define PIN_CAM_CS 15    // SPI chip select (10 kOhm pull-up to 3V3)
#define PIN_CAM_MISO 16  // camera -> ESP32
#define PIN_CAM_MOSI 17  // ESP32 -> camera
#define PIN_CAM_SCLK 18  // SPI clock

// ---- Display: ST7796S 4.0" 480x320 SPI + XPT2046 resistive touch -------------
#define PIN_TFT_BL 6      // backlight control ONLY on a driver-equipped display (Kconfig)
#define PIN_TFT_RST 7     // TFT RESET
#define PIN_TFT_DC 8      // TFT DC/RS
#define PIN_TOUCH_CS 9    // touch T_CS (10 kOhm pull-up to 3V3)
#define PIN_TFT_CS 10     // TFT CS     (10 kOhm pull-up to 3V3)
#define PIN_TFT_MOSI 11   // TFT MOSI + touch T_DIN (shared)
#define PIN_TFT_SCLK 12   // TFT SCK  + touch T_CLK (shared)
#define PIN_TOUCH_MISO 13 // touch T_DO -> ESP32 (TFT MISO/SDO stays unconnected)
#define PIN_TOUCH_IRQ 14  // touch T_IRQ -> ESP32

// Reserved / avoided (checked by tools/verify_project.py):
//   GPIO19/20 native USB, GPIO0/3/45/46 strapping, GPIO26-37 flash + octal PSRAM,
//   GPIO43/44 UART0 console.
