// Arducam Mini / Mini Plus (OV2640) capture wrapper.
// The ArduCAM library is kept inside camera.cpp only: its header defines
// Arduino-era macros that must not leak into C++ standard-library code.
#pragma once
#include <stddef.h>
#include <stdint.h>

struct CamStatus {
    bool spi_ok = false;       // ArduChip test register round-trip over SPI
    bool sensor_ok = false;    // OV2640 ID read over I2C
    uint8_t vid = 0, pid = 0;  // expected 0x26, 0x41 or 0x42
};

// Starts Arduino SPI (camera bus) + Wire (sensor registers) and configures JPEG 320x240.
CamStatus camera_begin();

// Captures one JPEG still into a PSRAM buffer owned by the caller (free with heap_caps_free).
// Returns false on timeout or a malformed frame. `len` is the trimmed JPEG length (SOI..EOI).
bool camera_capture_jpeg(uint8_t **buf, size_t *len, uint32_t timeout_ms = 3000);
