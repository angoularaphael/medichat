const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const http = require("http");

const COMPOSE_DIR = "D:\\PROBOOK 445 G7\\Desktop\\workshop\\EIR";
const APP_URL = "http://127.0.0.1:5173";

function probe(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(Boolean(res.statusCode && res.statusCode < 500));
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

function waitReady() {
  let left = 90;
  return new Promise((resolve) => {
    const tick = async () => {
      if (await probe(APP_URL)) {
        resolve(true);
        return;
      }
      left -= 1;
      if (left <= 0) {
        resolve(false);
        return;
      }
      setTimeout(tick, 2000);
    };
    tick();
  });
}

function page(title, body) {
  const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title></head><body style="margin:0;background:#0b1020;color:#e8eefc;font-family:Segoe UI,sans-serif;padding:28px"><h1 style="font-weight:500">${title}</h1><p style="font-size:16px;line-height:1.5;max-width:520px">${body}</p></body></html>`;
  return "data:text/html;charset=utf-8," + encodeURIComponent(html);
}

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 375,
    minHeight: 640,
    title: "EIR",
    backgroundColor: "#0b1020",
    autoHideMenuBar: true,
  });
  win.loadURL(page("EIR", "Demarrage de Docker, du bus MQTT et de MIMIR."));
  spawn("docker", ["compose", "up", "-d"], {
    cwd: COMPOSE_DIR,
    shell: true,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  }).unref();
  const ready = await waitReady();
  if (ready) {
    win.loadURL(APP_URL);
    return;
  }
  win.loadURL(
    page(
      "EIR",
      "Docker n'a pas ouvert l'interface. Verifie que Docker Desktop tourne, puis relance EIR.exe.",
    ),
  );
});

app.on("window-all-closed", () => {
  app.quit();
});
