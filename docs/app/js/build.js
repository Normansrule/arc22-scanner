// Build stages 0–7 (docs/BUILD_GUIDE.md) with PASS / FIX / STOP and notes.
import { download, el, store } from "./app.js";

const STAGES = [
  ["Measure your exact parts", "Calipers and photos for the display, camera, ESP32, plugged Dupont leads, button, charger and battery. Enter them in Measure, download my_units.toml, rebuild."],
  ["Print the three fit samples", "Screen bezel, camera nose and the wired ESP32 gauge at 100 %. Plug in every jumper and check the bundles bend inside the gauge frame."],
  ["Clearance, insertion and closing checks", "Read the recorded CAD checks. Zero failures, without removing any wire field or strain-relief allowance."],
  ["Print the shells and dry-fit", "Empty halves close by hand. Then install and wire everything: the right shell must close with gentle hand pressure before any screw."],
  ["Bench commission", "Case open. Power and charger behaviour, then display and touch, then camera image in commissioning mode."],
  ["Enable local inference", "Turn off commissioning mode. Scan, check that boxes line up, select an object, fetch the article or QR code. Measure the timing."],
  ["Monitored closed-case run", "Twenty scans over thirty minutes and one charge cycle with the case closed. No resets, no hot spots."],
  ["Update the files and tell the truth", "Record what passed and what failed in docs/VALIDATION.md. Never call it perfect-fit, fully tested or waterproof."],
];

export function initBuild() {
  let state = store.get("build", {});
  const list = document.getElementById("stages");
  const save = () => store.set("build", state);

  const render = () => {
    list.replaceChildren();
    STAGES.forEach(([title, text], i) => {
      const s = state[i] ?? {};
      const buttons = ["PASS", "FIX", "STOP"].map((v) =>
        el("button", {
          "data-v": v, "aria-pressed": String(s.v === v), text: v,
          onclick: () => { state[i] = { ...s, v: s.v === v ? undefined : v, at: new Date().toISOString().slice(0, 10) }; save(); render(); },
        }));
      const note = el("textarea", { "aria-label": `Notes for stage ${i}`, placeholder: "What you measured, saw or changed" });
      note.value = s.note ?? "";
      note.addEventListener("change", () => { state[i] = { ...(state[i] ?? {}), note: note.value }; save(); });
      list.append(el("li", { class: "stage-item" },
        el("span", { class: "num", text: String(i) }),
        el("div", {},
          el("h2", { text: title }),
          el("p", { text }),
          el("div", { class: "verdicts", role: "group", "aria-label": `Result for stage ${i}` }, buttons),
          note)));
    });
  };
  render();

  document.getElementById("b-download").addEventListener("click", () => {
    const lines = ["# ARC-22 build progress", "", "| Stage | Result | Date | Notes |", "|---|---|---|---|"];
    STAGES.forEach(([title], i) => {
      const s = state[i] ?? {};
      lines.push(`| ${i} ${title} | ${s.v ?? "not done"} | ${s.v ? s.at ?? "" : ""} | ${(s.note ?? "").replace(/\n/g, " ").replace(/\|/g, "/")} |`);
    });
    download("arc22-build-progress.md", lines.join("\n") + "\n", "text/markdown");
  });
  document.getElementById("b-clear").addEventListener("click", () => {
    if (!confirm("Reset every stage result and note?")) return;
    state = {};
    save();
    render();
  });
}
