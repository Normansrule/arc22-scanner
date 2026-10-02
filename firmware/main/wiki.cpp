#include "wiki.h"

#include <Arduino.h>
#include <WiFi.h>

#include "cJSON.h"
#include "coco_labels.h"
#include "esp_crt_bundle.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "nvs.h"
#include "sdkconfig.h"

// Wi-Fi credentials come from main/secrets.h, generated from the repo-root .env by
// `python tools/fetch_libraries.py --secrets`. secrets.h is git-ignored. Without it the
// scanner stays offline and falls back to the QR code.
#if __has_include("secrets.h")
#include "secrets.h"
#define ARC_HAVE_SECRETS 1
#else
#define ARC_HAVE_SECRETS 0
#endif

static const char *TAG = "wiki";
static const size_t kMaxBody = 12 * 1024;
static const size_t kMaxExtract = 1800;

bool wiki_has_credentials() { return ARC_HAVE_SECRETS; }

std::string wiki_url(int i) {
    return std::string("https://") + CONFIG_ARC_WIKI_LANG + ".wikipedia.org/wiki/" + coco_label(i).wiki;
}

std::string google_url(int i) {
    std::string q = coco_label(i).name;
    for (auto &c : q)
        if (c == ' ') c = '+';
    return "https://www.google.com/search?q=" + q;
}

static bool cache_get(int i, WikiResult &r) {
    nvs_handle_t h;
    if (nvs_open("wiki", NVS_READONLY, &h) != ESP_OK) return false;
    char key[8];
    snprintf(key, sizeof key, "c%02d", i);
    size_t len = 0;
    bool ok = nvs_get_str(h, key, nullptr, &len) == ESP_OK && len > 1;
    if (ok) {
        std::string s(len, '\0');
        ok = nvs_get_str(h, key, s.data(), &len) == ESP_OK;
        s.resize(len ? len - 1 : 0);
        r.extract = s;
        r.title = coco_label(i).wiki;
        r.from_cache = true;
        r.ok = ok;
    }
    nvs_close(h);
    return ok;
}

static void cache_put(int i, const std::string &text) {
    nvs_handle_t h;
    if (nvs_open("wiki", NVS_READWRITE, &h) != ESP_OK) return;
    char key[8];
    snprintf(key, sizeof key, "c%02d", i);
    nvs_set_str(h, key, text.c_str());
    nvs_commit(h);
    nvs_close(h);
}

void wifi_off() {
    WiFi.disconnect(true, false);
    WiFi.mode(WIFI_OFF);
}

static bool wifi_on(uint32_t timeout_ms) {
#if ARC_HAVE_SECRETS
    WiFi.mode(WIFI_STA);
    WiFi.begin(ARC_WIFI_SSID, ARC_WIFI_PASSWORD);
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < timeout_ms) delay(100);
    return WiFi.status() == WL_CONNECTED;
#else
    (void)timeout_ms;
    return false;
#endif
}

struct Body {
    char *buf;
    size_t len;
};

static esp_err_t on_event(esp_http_client_event_t *e) {
    if (e->event_id == HTTP_EVENT_ON_DATA && e->user_data) {
        Body *b = (Body *)e->user_data;
        size_t n = e->data_len;
        if (b->len + n >= kMaxBody) n = kMaxBody - 1 - b->len;
        memcpy(b->buf + b->len, e->data, n);
        b->len += n;
    }
    return ESP_OK;
}

WikiResult wiki_lookup(int i) {
    WikiResult r;
    if (cache_get(i, r)) return r;
    if (!ARC_HAVE_SECRETS) {
        r.error = "offline (no Wi-Fi credentials)";
        return r;
    }
    if (!wifi_on(12000)) {
        r.error = "Wi-Fi connect failed";
        wifi_off();
        return r;
    }
    Body body{(char *)heap_caps_calloc(1, kMaxBody, MALLOC_CAP_SPIRAM), 0};
    std::string url = std::string("https://") + CONFIG_ARC_WIKI_LANG +
                      ".wikipedia.org/api/rest_v1/page/summary/" + coco_label(i).wiki;
    esp_http_client_config_t cfg = {};
    cfg.url = url.c_str();
    cfg.crt_bundle_attach = esp_crt_bundle_attach;
    cfg.event_handler = on_event;
    cfg.user_data = &body;
    cfg.timeout_ms = 10000;
    cfg.buffer_size = 2048;
    esp_http_client_handle_t c = esp_http_client_init(&cfg);
    // Wikimedia asks every client for a descriptive User-Agent.
    esp_http_client_set_header(c, "User-Agent", "ARC22-Scanner/1.0 (open-source handheld; esp_http_client)");
    esp_http_client_set_header(c, "Accept", "application/json");
    esp_err_t err = esp_http_client_perform(c);
    int status = esp_http_client_get_status_code(c);
    esp_http_client_cleanup(c);
    wifi_off();
    if (err != ESP_OK || status != 200 || !body.buf) {
        r.error = "HTTP error " + std::to_string(status);
        heap_caps_free(body.buf);
        return r;
    }
    cJSON *j = cJSON_ParseWithLength(body.buf, body.len);
    heap_caps_free(body.buf);
    const cJSON *ex = j ? cJSON_GetObjectItemCaseSensitive(j, "extract") : nullptr;
    const cJSON *ti = j ? cJSON_GetObjectItemCaseSensitive(j, "title") : nullptr;
    if (cJSON_IsString(ex) && ex->valuestring) {
        r.extract = ex->valuestring;
        if (r.extract.size() > kMaxExtract) r.extract = r.extract.substr(0, kMaxExtract) + "...";
        r.title = cJSON_IsString(ti) ? ti->valuestring : coco_label(i).wiki;
        r.ok = true;
        cache_put(i, r.extract);
    } else {
        r.error = "unexpected response";
    }
    cJSON_Delete(j);
    ESP_LOGI(TAG, "lookup %s: %s", coco_label(i).wiki, r.ok ? "ok" : r.error.c_str());
    return r;
}
