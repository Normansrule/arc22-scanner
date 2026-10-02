// 3D viewer: shells (white/cyan regions), electronics, reserved space, cable routes.
// Assembly coordinates straight from the CAD: X front-back, Y width (seam at 0), Z up, mm.
import * as THREE from "../lib/three/three.module.js";
import { OrbitControls } from "../lib/three/addons/controls/OrbitControls.js";
import { STLLoader } from "../lib/three/addons/loaders/STLLoader.js";
import { getJSON } from "./app.js";

const CENTER = new THREE.Vector3(109, 0, 109);
// view directions (from the model centre toward the camera)
const CAMS = {
  front: new THREE.Vector3(0.62, -0.62, 0.42),
  rear: new THREE.Vector3(-0.62, 0.66, 0.36),
  inside: new THREE.Vector3(0.0, 1.0, 0.05),
  top: new THREE.Vector3(0.0, -0.12, 1.0),
};
const RADIUS = 172; // bounding sphere of the scanner incl. the lifted right shell, mm

export async function initViewer() {
  const canvas = document.getElementById("viewport");
  const stage = canvas.parentElement;
  const loading = document.getElementById("loading");
  const hover = document.getElementById("hover-label");

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 1, 5000);
  camera.up.set(0, 0, 1);
  let lastDir = CAMS.front.clone();
  const frame = (dir) => {
    lastDir = dir.clone().normalize();
    const vf = THREE.MathUtils.degToRad(camera.fov) / 2;
    const hf = Math.atan(Math.tan(vf) * camera.aspect);
    const dist = (RADIUS / Math.sin(Math.min(vf, hf))) * 1.02;
    camera.position.copy(CENTER).addScaledVector(lastDir, dist);
  };
  frame(CAMS.front);
  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(CENTER);
  controls.enableDamping = false;
  controls.update();

  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899a6, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(300, -400, 600);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xcfe9f7, 0.9);
  rim.position.set(-400, 300, 200);
  scene.add(rim);

  const groups = {};
  for (const g of ["LEFT", "RIGHT", "modules", "fields", "routes"]) {
    groups[g] = new THREE.Group();
    groups[g].name = g;
    scene.add(groups[g]);
  }

  let dirty = true;
  const render = () => { dirty = true; };
  controls.addEventListener("change", render);
  (function loop() {
    if (dirty) { renderer.render(scene, camera); dirty = false; }
    requestAnimationFrame(loop);
  })();

  const resize = () => {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    const first = camera.aspect === 1;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (first) { frame(lastDir); controls.update(); }
    render();
  };
  new ResizeObserver(resize).observe(stage);

  // ---- load meshes ----
  const index = await getJSON("models/index.json");
  const loader = new STLLoader();
  const pickable = [];
  await Promise.all(index.meshes.map(async (m) => {
    const buf = await (await fetch("models/" + m.file)).arrayBuffer();
    const geo = loader.parse(buf);
    geo.computeVertexNormals();
    let mat;
    if (m.layer === "fields") {
      mat = new THREE.MeshStandardMaterial({ color: m.colour, transparent: true, opacity: 0.38, depthWrite: false, roughness: 0.8 });
    } else if (m.layer === "routes") {
      mat = new THREE.MeshStandardMaterial({ color: m.colour, transparent: true, opacity: 0.85, roughness: 0.6 });
    } else if (m.layer === "shells") {
      mat = new THREE.MeshStandardMaterial({ color: m.colour, roughness: 0.55, metalness: 0.0, side: THREE.DoubleSide });
    } else {
      mat = new THREE.MeshStandardMaterial({ color: m.colour, roughness: 0.5, metalness: 0.1 });
    }
    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData.label = m.label;
    const group = m.layer === "shells" ? groups[m.side] : groups[m.layer];
    group.add(mesh);
    if (m.layer !== "fields") pickable.push(mesh);
  }));
  loading.hidden = true;
  resize();

  // ---- layers ----
  for (const box of document.querySelectorAll(".layers input")) {
    const apply = () => { groups[box.dataset.layer].visible = box.checked; render(); };
    box.addEventListener("change", apply);
    apply();
  }

  // ---- closing the right shell ----
  const slider = document.getElementById("close");
  const out = document.getElementById("close-out");
  const verdict = document.getElementById("close-verdict");
  let closing = null;
  try {
    const checks = await getJSON("data/checks.json");
    closing = checks.cad_checks?.checks.filter((c) => c.group === "closing swept volume") ?? null;
  } catch { closing = null; }
  const applyClose = () => {
    const h = Number(slider.value);
    groups.RIGHT.position.y = h;
    out.textContent = h === 0 ? "Seated" : `${h} mm`;
    if (h > 0) {
      verdict.textContent = "Keep lowering. Watch the amber space: no plastic may enter it on the way down.";
    } else if (closing && closing.length) {
      const ok = closing.every((c) => c.result === "PASS");
      verdict.textContent = ok
        ? `Recorded check passes: the right shell crosses no plugged connector, wire field or route on the way down (${closing[0].value}), at the nominal measurements. Confirm it by hand in Stage 3.`
        : `Recorded check FAILS: ${closing.filter((c) => c.result !== "PASS").map((c) => c.value).join(", ")}. See Checks.`;
    } else {
      verdict.textContent = "Seated. Run the CAD checks to record the closing result.";
    }
    render();
  };
  slider.addEventListener("input", applyClose);
  applyClose();

  // ---- camera presets ----
  for (const b of document.querySelectorAll("[data-cam]")) {
    b.addEventListener("click", () => {
      controls.target.copy(CENTER);
      frame(CAMS[b.dataset.cam]);
      controls.update();
      if (b.dataset.cam === "inside") {
        const right = document.querySelector('.layers input[data-layer="RIGHT"]');
        right.checked = false;
        right.dispatchEvent(new Event("change"));
      }
      render();
    });
  }

  // ---- hover labels ----
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let pending = false;
  canvas.addEventListener("pointermove", (e) => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      const r = canvas.getBoundingClientRect();
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      const hit = ray.intersectObjects(pickable.filter((m) => m.parent.visible), false)[0];
      hover.textContent = hit ? hit.object.userData.label : "";
    });
  });
  canvas.addEventListener("pointerleave", () => { hover.textContent = ""; });

  // ---- facts ----
  try {
    const b = await getJSON("data/build.json");
    const bb = b.bounds.LEFT;
    document.getElementById("model-facts").textContent =
      `Envelope ${Math.round(bb[1] - bb[0])} × 118 × ${Math.round(bb[5] - bb[4])} mm. ` +
      `${b.screws.length} M2 × 12 screws clamp shell to shell only. Drag to orbit, scroll or pinch to zoom.`;
  } catch { /* optional */ }
}
