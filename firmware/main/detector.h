// Local COCO object detection on the ESP32-S3 (no cloud, no PC).
#pragma once
#include <stddef.h>
#include <stdint.h>

struct Detection {
    int category;   // COCO index 0..79
    float score;    // 0..1
    int x1, y1, x2, y2;  // pixels in the 320x240 capture
};

struct DetectResult {
    bool ok = false;
    int count = 0;
    Detection det[8];
    uint32_t decode_ms = 0, infer_ms = 0;
    size_t psram_free_before = 0, psram_free_after = 0;
};

// Decodes the JPEG, runs YOLO11N_320_S8_V1 from the coco_det flash partition,
// keeps the best `max_det`, then DELETES the detector and the decoded image so
// the memory is back before Wi-Fi/TLS starts.
DetectResult detector_run(const uint8_t *jpeg, size_t len, float score_thr, int max_det);
