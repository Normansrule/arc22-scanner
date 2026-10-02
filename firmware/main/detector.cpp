#include "detector.h"

#include <algorithm>
#include <vector>

#include "coco_detect.hpp"
#include "dl_image_jpeg.hpp"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"

static const char *TAG = "detector";

DetectResult detector_run(const uint8_t *jpeg, size_t len, float score_thr, int max_det) {
    DetectResult r;
    r.psram_free_before = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    int64_t t0 = esp_timer_get_time();

    dl::image::jpeg_img_t jpg = {.data = (void *)jpeg, .data_len = len};
    dl::image::img_t img = dl::image::sw_decode_jpeg(jpg, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    if (!img.data) {
        ESP_LOGE(TAG, "JPEG decode failed");
        return r;
    }
    int64_t t1 = esp_timer_get_time();
    r.decode_ms = (uint32_t)((t1 - t0) / 1000);

    // Weights stay in flash: with 8 MB PSRAM the component does not copy parameters.
    COCODetect *detect = new COCODetect(COCODetect::YOLO11N_320_S8_V1);
    detect->set_score_thr(score_thr);
    std::vector<Detection> found;
    {
        auto &res = detect->run(img);
        for (const auto &d : res) {
            if (d.box.size() < 4) continue;
            found.push_back({d.category, d.score, d.box[0], d.box[1], d.box[2], d.box[3]});
        }
    }
    int64_t t2 = esp_timer_get_time();
    r.infer_ms = (uint32_t)((t2 - t1) / 1000);

    // Release every inference allocation before anything else (Wi-Fi/TLS) runs.
    delete detect;
    heap_caps_free(img.data);

    std::sort(found.begin(), found.end(), [](const Detection &a, const Detection &b) { return a.score > b.score; });
    r.count = std::min<int>((int)found.size(), std::min(max_det, 8));
    for (int i = 0; i < r.count; i++) r.det[i] = found[i];
    r.ok = true;
    r.psram_free_after = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    ESP_LOGI(TAG, "decode %u ms, inference %u ms, %d objects, PSRAM free %u -> %u", (unsigned)r.decode_ms,
             (unsigned)r.infer_ms, r.count, (unsigned)r.psram_free_before, (unsigned)r.psram_free_after);
    return r;
}
