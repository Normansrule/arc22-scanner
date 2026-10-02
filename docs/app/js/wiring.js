// Pin table, generated from firmware/main/pins.h via tools/build_web_data.py.
import { el, getJSON } from "./app.js";

const NAMES = {
  PIN_CAM_SDA: "Camera SDA", PIN_CAM_SCL: "Camera SCL", PIN_CAM_CS: "Camera CS", PIN_CAM_MISO: "Camera MISO",
  PIN_CAM_MOSI: "Camera MOSI", PIN_CAM_SCLK: "Camera SCLK", PIN_TFT_BL: "TFT backlight", PIN_TFT_RST: "TFT RESET",
  PIN_TFT_DC: "TFT DC/RS", PIN_TOUCH_CS: "Touch T_CS", PIN_TFT_CS: "TFT CS", PIN_TFT_MOSI: "TFT MOSI + touch T_DIN",
  PIN_TFT_SCLK: "TFT SCK + touch T_CLK", PIN_TOUCH_MISO: "Touch T_DO", PIN_TOUCH_IRQ: "Touch T_IRQ",
};

export async function initWiring() {
  const pins = await getJSON("data/pins.json");
  const body = document.querySelector("#pin-table tbody");
  pins.sort((a, b) => a.gpio - b.gpio);
  for (const p of pins) {
    body.append(el("tr", {},
      el("td", { class: "gpio", text: `GPIO${p.gpio}` }),
      el("td", { text: NAMES[p.name] ?? p.name }),
      el("td", { class: "small", text: p.note })));
  }
}
