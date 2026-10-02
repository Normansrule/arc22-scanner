// LovyanGFX configuration: ST7796S panel + XPT2046 touch sharing one SPI bus.
// The display bus uses SPI3_HOST so that Arduino's global SPI (SPI2/FSPI) is free
// for the Arducam driver, which talks through the Arduino SPI object.
#pragma once
#define LGFX_USE_V1
#include <LovyanGFX.hpp>

#include "pins.h"
#include "sdkconfig.h"

class LGFX : public lgfx::LGFX_Device {
    lgfx::Panel_ST7796 panel_;
    lgfx::Bus_SPI bus_;
    lgfx::Touch_XPT2046 touch_;
#if CONFIG_ARC_BACKLIGHT_GPIO_ENABLED
    lgfx::Light_PWM light_;
#endif

   public:
    LGFX() {
        {
            auto cfg = bus_.config();
            cfg.spi_host = SPI3_HOST;
            cfg.spi_mode = 0;
            cfg.freq_write = 27000000;  // lower to 20 MHz if you see noise on long jumpers
            cfg.freq_read = 8000000;
            cfg.spi_3wire = false;
            cfg.use_lock = true;
            cfg.dma_channel = SPI_DMA_CH_AUTO;
            cfg.pin_sclk = PIN_TFT_SCLK;
            cfg.pin_mosi = PIN_TFT_MOSI;
            cfg.pin_miso = PIN_TOUCH_MISO;  // only the touch controller drives this line
            cfg.pin_dc = PIN_TFT_DC;
            bus_.config(cfg);
            panel_.setBus(&bus_);
        }
        {
            auto cfg = panel_.config();
            cfg.pin_cs = PIN_TFT_CS;
            cfg.pin_rst = PIN_TFT_RST;
            cfg.pin_busy = -1;
            cfg.panel_width = 320;
            cfg.panel_height = 480;
            cfg.offset_x = 0;
            cfg.offset_y = 0;
            cfg.offset_rotation = 0;
            cfg.readable = false;  // TFT MISO/SDO is not wired
            cfg.invert = false;    // VERIFY: some ST7796S modules need true
            cfg.rgb_order = false; // VERIFY: swap if red/blue look exchanged
            cfg.dlen_16bit = false;
            cfg.bus_shared = true;
            panel_.config(cfg);
        }
#if CONFIG_ARC_BACKLIGHT_GPIO_ENABLED
        {
            auto cfg = light_.config();
            cfg.pin_bl = PIN_TFT_BL;
            cfg.invert = false;
            cfg.freq = 12000;
            cfg.pwm_channel = 7;
            light_.config(cfg);
            panel_.setLight(&light_);
        }
#endif
        {
            auto cfg = touch_.config();
            cfg.x_min = 0;
            cfg.x_max = 4095;
            cfg.y_min = 0;
            cfg.y_max = 4095;
            cfg.pin_int = PIN_TOUCH_IRQ;
            cfg.bus_shared = true;
            cfg.offset_rotation = 0;
            cfg.spi_host = SPI3_HOST;
            cfg.freq = 1000000;
            cfg.pin_sclk = PIN_TFT_SCLK;
            cfg.pin_mosi = PIN_TFT_MOSI;
            cfg.pin_miso = PIN_TOUCH_MISO;
            cfg.pin_cs = PIN_TOUCH_CS;
            touch_.config(cfg);
            panel_.setTouch(&touch_);
        }
        setPanel(&panel_);
    }
};

// Global display object (defined in display.cpp)
extern LGFX lcd;

// Loads touch calibration from NVS, or runs the 4-corner calibration and stores it.
void display_begin(bool force_calibration);
bool display_has_backlight_control();
void display_set_dim(bool dim);
