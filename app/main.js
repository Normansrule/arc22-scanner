// ARC-22 Studio desktop app: the same web app as GitHub Pages (docs/app), served
// from inside the package through a private, secure "arc22://" scheme so ES modules,
// fetch() of the models and the offline data all work without a web server.
const { app, BrowserWindow, protocol, net, shell, session } = require("electron");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const WEB = path.join(__dirname, "web");
protocol.registerSchemesAsPrivileged([
  { scheme: "arc22", privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true } },
]);

if (!app.requestSingleInstanceLock()) app.quit();

function serve() {
  protocol.handle("arc22", (req) => {
    const url = new URL(req.url);
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, "") || "index.html";
    const file = path.normalize(path.join(WEB, rel));
    if (!file.startsWith(WEB + path.sep)) return new Response("Not found", { status: 404 });
    return net.fetch(pathToFileURL(file).toString());
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 380,
    minHeight: 560,
    title: "ARC-22 Studio",
    backgroundColor: "#e3eaee",
    icon: path.join(__dirname, "build", "icon.png"),
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  // Links that leave the app (datasheets, GitHub) open in the normal browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith("arc22://")) {
      e.preventDefault();
      if (/^https?:/.test(url)) shell.openExternal(url);
    }
  });
  win.loadURL("arc22://studio/index.html#model");
  return win;
}

app.whenReady().then(() => {
  serve();
  // No camera/microphone/etc. needed: refuse every permission request.
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, cb) => cb(false));
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("second-instance", () => {
  const [w] = BrowserWindow.getAllWindows();
  if (w) { if (w.isMinimized()) w.restore(); w.focus(); }
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
