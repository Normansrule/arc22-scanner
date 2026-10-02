idf_component_register(
    SRCS "main.cpp" "display.cpp" "camera.cpp" "detector.cpp" "wiki.cpp" "ui.cpp"
    INCLUDE_DIRS "."
    REQUIRES arduino-esp32 LovyanGFX ArduCAM esp-dl coco_detect
             esp_http_client esp-tls nvs_flash json mbedtls esp_wifi
)
