// Recorded CAD + mesh checks (docs/validation/*.json, copied by tools/build_web_data.py).
import { el, getJSON } from "./app.js";

export async function initChecks() {
  const data = await getJSON("data/checks.json");
  const cad = data.cad_checks;
  const host = document.getElementById("c-groups");
  const lede = document.getElementById("c-lede");
  if (!cad) {
    lede.textContent = "No checks recorded yet. Run bash scripts/rebuild_all.sh.";
    return;
  }
  const s = cad.summary;
  lede.textContent = `${s.passed} of ${s.total} passed, ${s.failed} failed. These check the model against itself with ` +
    `${s.unverified_measurements} measurements still at reference values — they are not physical tests.`;

  const groups = new Map();
  for (const c of cad.checks) {
    if (!groups.has(c.group)) groups.set(c.group, []);
    groups.get(c.group).push(c);
  }
  const fails = document.getElementById("c-fails");
  const draw = () => {
    host.replaceChildren();
    for (const [g, list] of groups) {
      const rows = fails.checked ? list.filter((c) => c.result !== "PASS") : list;
      if (!rows.length) continue;
      const passed = list.filter((c) => c.result === "PASS").length;
      host.append(el("section", { class: "cgroup" },
        el("h2", { text: `${g[0].toUpperCase()}${g.slice(1)} (${passed} / ${list.length})` }),
        el("table", {},
          el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "Item" }), el("th", { scope: "col", text: "Result" }),
            el("th", { scope: "col", text: "Value" }))),
          el("tbody", {}, rows.map((c) => el("tr", {},
            el("td", {}, c.item, c.note ? el("div", { class: "small", text: c.note }) : null),
            el("td", { class: `res ${c.result}`, text: c.result }),
            el("td", { class: "small", text: c.value })))))));
    }
    if (!host.children.length) host.append(el("p", { text: "No failures recorded." }));
    const m = data.mesh_checks;
    if (m && !fails.checked) {
      host.append(el("section", { class: "cgroup" },
        el("h2", { text: `Exported print meshes (${m.all_pass ? "all pass" : "FAIL"})` }),
        el("table", {},
          el("thead", {}, el("tr", {}, ["File", "Watertight", "Triangles", "Volume Δ %"].map((t) => el("th", { scope: "col", text: t })))),
          el("tbody", {}, m.meshes.map((r) => el("tr", {},
            el("td", { text: r.file }), el("td", { class: `res ${r.watertight ? "PASS" : "FAIL"}`, text: r.watertight ? "PASS" : "FAIL" }),
            el("td", { text: String(r.triangles) }), el("td", { text: String(r.volume_error_pct) })))))));
    }
  };
  fails.addEventListener("change", draw);
  draw();
}
