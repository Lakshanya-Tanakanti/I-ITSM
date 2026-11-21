// TC-29: network failure shown as a readable message (headless Chrome).
// Usage: npm install puppeteer-core; set CHROME to a Chrome binary and PYTHON to the backend venv python; node docs/tools/e2e_tc29_network_failure.mjs
import { spawn } from "node:child_process";
import puppeteer from "puppeteer-core";
const REPO = process.env.REPO || new URL("../..", import.meta.url).pathname.replace(/\/$/, "");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(url, tries = 60) { for (let i = 0; i < tries; i++) { try { const r = await fetch(url); if (r.status < 500) return; } catch {} await sleep(500); } throw new Error("timeout " + url); }
const env = { ...process.env, DATABASE_URL: "sqlite:////tmp/e2e_itsm.db", SLA_MONITOR_ENABLED: "false" };
const backend = spawn(process.env.PYTHON || "python", ["-m", "uvicorn", "app.main:app", "--port", "8000"], { cwd: REPO + "/backend", env, stdio: "ignore", detached: true });
const vite = spawn("npx", ["vite", "--port", "5173", "--strictPort"], { cwd: REPO + "/frontend", stdio: "ignore", detached: true });
const kill = (p) => { try { process.kill(-p.pid, "SIGTERM"); } catch {} };
const out = {};
try {
  await waitFor("http://localhost:8000/health"); await waitFor("http://localhost:5173/");
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME || "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
  const page = await browser.newPage(); await page.setViewport({ width: 1280, height: 760 });
  const jsErrors = []; page.on("pageerror", (e) => jsErrors.push(String(e)));
  await page.goto("http://localhost:5173/login", { waitUntil: "networkidle0" });
  const inputs = await page.$$("input");
  await inputs[0].type("admin@iitsm.example.com"); await inputs[1].type("Admin@123");
  // Sanity: the back end answers through the proxy.
  out.healthViaProxy = (await (await fetch("http://localhost:5173/api/auth/me")).status);
  // Case A: back end stopped, Vite proxy still running.
  kill(backend); await sleep(1500);
  await page.click("button.btn.primary"); await sleep(2500);
  out.caseA = await page.evaluate(() => document.body.innerText.match(/Cannot reach the server[^\n]*|Request failed[^\n]*/)?.[0] || null);
  await page.screenshot({ path: "SS-29a_backend_stopped.png" });
  // Case B: front-end server stopped as well, page still open.
  kill(vite); await sleep(1500);
  await page.click("button.btn.primary"); await sleep(2500);
  out.caseB = await page.evaluate(() => document.body.innerText.match(/Cannot reach the server[^\n]*|Request failed[^\n]*/)?.[0] || null);
  out.pageStillRendered = await page.evaluate(() => document.body.innerText.includes("Sign in"));
  await page.screenshot({ path: "SS-29b_frontend_stopped.png" });
  out.jsErrors = jsErrors; out.when = new Date().toISOString();
  await browser.close();
} finally { kill(backend); kill(vite); }
console.log(JSON.stringify(out, null, 2));
