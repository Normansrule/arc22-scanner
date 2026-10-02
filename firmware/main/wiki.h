// Wikipedia "intro" lookup: NVS cache first, then Wi-Fi + HTTPS (REST summary API).
// Wi-Fi is ONLY used here, never during detection.
#pragma once
#include <string>

struct WikiResult {
    bool ok = false;
    bool from_cache = false;
    std::string title;
    std::string extract;  // plain-text intro
    std::string error;
};

bool wiki_has_credentials();
WikiResult wiki_lookup(int coco_index);
std::string wiki_url(int coco_index);    // for the QR fallback
std::string google_url(int coco_index);  // second fallback
void wifi_off();
