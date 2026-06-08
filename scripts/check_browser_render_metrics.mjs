#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

function fail(message) {
  console.error(`[FAIL] ${message}`);
  process.exit(1);
}

function ok(message) {
  console.log(`[OK] ${message}`);
}

function parseArgs(argv) {
  const args = { root: ".", cases: "tests/browser_render_metric_cases.json" };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--root") {
      args.root = argv[++i];
    } else if (arg === "--cases") {
      args.cases = argv[++i];
    } else if (arg === "--chrome") {
      args.chrome = argv[++i];
    } else {
      fail(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function chromeCandidates(explicitPath) {
  return [
    explicitPath,
    process.env.CHROME_PATH,
    process.env.BROWSER_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
}

function findChrome(explicitPath) {
  for (const candidate of chromeCandidates(explicitPath)) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForProcessExit(child, timeoutMs = 2000) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        resolve();
      }
    };
    child.once("exit", finish);
    setTimeout(finish, timeoutMs);
  });
}

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          body += chunk;
        });
        res.on("end", () => {
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        });
      })
      .on("error", reject);
  });
}

function connectWebSocket(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const key = Buffer.from(`${Date.now()}-${Math.random()}`).toString("base64");
    const socket = http.request({
      host: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname + parsed.search,
      headers: {
        Connection: "Upgrade",
        Upgrade: "websocket",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": key,
      },
    });
    socket.on("upgrade", (_res, rawSocket) => {
      resolve(rawSocket);
    });
    socket.on("error", reject);
    socket.end();
  });
}

function encodeWsFrame(payload) {
  const data = Buffer.from(payload);
  const length = data.length;
  let header;
  if (length < 126) {
    header = Buffer.alloc(6);
    header[0] = 0x81;
    header[1] = 0x80 | length;
    header.writeUInt32BE(0, 2);
  } else if (length < 65536) {
    header = Buffer.alloc(8);
    header[0] = 0x81;
    header[1] = 0x80 | 126;
    header.writeUInt16BE(length, 2);
    header.writeUInt32BE(0, 4);
  } else {
    fail("WebSocket payload too large");
  }
  return Buffer.concat([header, data]);
}

function createCdpClient(socket) {
  let nextId = 1;
  let buffer = Buffer.alloc(0);
  const pending = new Map();

  function parseFrames() {
    while (buffer.length >= 2) {
      const first = buffer[0];
      const second = buffer[1];
      let offset = 2;
      let length = second & 0x7f;
      if (length === 126) {
        if (buffer.length < 4) return;
        length = buffer.readUInt16BE(2);
        offset = 4;
      } else if (length === 127) {
        fail("Unsupported large WebSocket frame");
      }
      const masked = Boolean(second & 0x80);
      const maskOffset = masked ? 4 : 0;
      if (buffer.length < offset + maskOffset + length) return;
      let payload = buffer.subarray(offset + maskOffset, offset + maskOffset + length);
      if (masked) {
        const mask = buffer.subarray(offset, offset + 4);
        payload = Buffer.from(payload.map((value, index) => value ^ mask[index % 4]));
      }
      buffer = buffer.subarray(offset + maskOffset + length);
      if ((first & 0x0f) === 0x8) continue;
      const message = JSON.parse(payload.toString("utf8"));
      if (message.id && pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message || "CDP error"));
        else resolve(message.result);
      }
    }
  }

  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    parseFrames();
  });

  return {
    send(method, params = {}) {
      const id = nextId++;
      const payload = JSON.stringify({ id, method, params });
      socket.write(encodeWsFrame(payload));
      return new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
      });
    },
    close() {
      socket.end();
    },
  };
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function makeHarness(fragment, caseId) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${caseId}</title>
<style>
:root {
  --color-background-primary:#262624;
  --color-background-secondary:#333330;
  --color-background-info:#0c447c;
  --color-background-warning:#633806;
  --color-background-success:#085041;
  --color-border-secondary:#666;
  --color-border-tertiary:rgba(222,220,209,.3);
  --color-text-primary:#faf9f5;
  --color-text-secondary:#c2c0b6;
  --color-text-tertiary:#888780;
  --color-text-info:#85b7eb;
  --color-text-warning:#ef9f27;
  --color-text-success:#5dcaa5;
  --border-radius-lg:8px;
}
* { box-sizing:border-box; }
body { margin:0; padding:16px; background:#1f1f1d; color:#faf9f5; font-family:Arial, sans-serif; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
#mount { width:100%; max-width:760px; margin:0 auto; }
button { font:inherit; }
</style>
</head>
<body>
<main id="mount">${fragment}</main>
<script>
window.sendPrompt = function(){};
</script>
</body>
</html>`;
}

function metricExpression(caseType) {
  return `(() => {
    const body = document.body;
    const doc = document.documentElement;
    const buttons = Array.from(document.querySelectorAll('button')).map((el) => {
      const r = el.getBoundingClientRect();
      return { text: el.textContent.trim(), width: r.width, height: r.height, visible: r.width > 0 && r.height > 0 };
    });
    const svgs = Array.from(document.querySelectorAll('svg')).map((el) => {
      const r = el.getBoundingClientRect();
      return { width: r.width, height: r.height, visible: r.width > 0 && r.height > 0 };
    });
    const cards = Array.from(document.querySelectorAll('.mod-card')).map((el) => {
      const r = el.getBoundingClientRect();
      return { width: r.width, height: r.height, visible: r.width > 0 && r.height > 0 };
    });
    const overflowingElements = Array.from(document.querySelectorAll('#mount, .mod-grid, .mod-card, .mod-item, .mod-title, .mod-sub, .fl-step')).filter((el) => {
      return el.scrollWidth > el.clientWidth + 1;
    }).map((el) => {
      return { tag: el.tagName.toLowerCase(), className: el.className || '', scrollWidth: el.scrollWidth, clientWidth: el.clientWidth };
    });
    const steps = Array.from(document.querySelectorAll('.fl-step')).map((el) => {
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return { active: el.classList.contains('active'), display: style.display, width: r.width, height: r.height };
    });
    return {
      type: ${JSON.stringify(caseType)},
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      scrollWidth: Math.max(body.scrollWidth, doc.scrollWidth),
      clientWidth: doc.clientWidth,
      overflowingElements,
      buttons,
      svgs,
      cards,
      steps
    };
  })()`;
}

function assertMetrics(caseId, viewport, caseType, assertions, metrics) {
  if (assertions.includes("noHorizontalOverflow")) {
    if (metrics.scrollWidth > metrics.clientWidth + 1) {
      throw new Error(`${caseId} viewport ${viewport}: horizontal overflow ${metrics.scrollWidth} > ${metrics.clientWidth}`);
    }
    if (metrics.overflowingElements.length) {
      const item = metrics.overflowingElements[0];
      throw new Error(`${caseId} viewport ${viewport}: horizontal overflow inside ${item.tag}.${item.className} ${item.scrollWidth} > ${item.clientWidth}`);
    }
  }
  if (assertions.includes("clickTargets")) {
    for (const button of metrics.buttons) {
      if (!button.visible || button.width < 32 || button.height < 32) {
        throw new Error(`${caseId} viewport ${viewport}: click target too small (${button.width}x${button.height})`);
      }
    }
  }
  if (assertions.includes("svgVisible")) {
    if (!metrics.svgs.length) throw new Error(`${caseId} viewport ${viewport}: no SVG rendered`);
    const visibleSvgs = metrics.svgs.filter((svg) => svg.visible);
    if (!visibleSvgs.length) throw new Error(`${caseId} viewport ${viewport}: no visible SVG rendered`);
    for (const svg of visibleSvgs) {
      if (!svg.visible || svg.width < 240 || svg.width > metrics.clientWidth) {
        throw new Error(`${caseId} viewport ${viewport}: SVG visible size invalid (${svg.width}x${svg.height})`);
      }
    }
  }
  if (assertions.includes("cardsVisible")) {
    if (!metrics.cards.length) throw new Error(`${caseId} viewport ${viewport}: no cards rendered`);
    for (const card of metrics.cards) {
      if (!card.visible || card.width < 140 || card.width > metrics.clientWidth) {
        throw new Error(`${caseId} viewport ${viewport}: card visible size invalid (${card.width}x${card.height})`);
      }
    }
  }
  if (assertions.includes("singleActiveStep")) {
    const activeVisible = metrics.steps.filter((step) => step.active && step.display !== "none" && step.width > 0 && step.height > 0);
    const inactiveVisible = metrics.steps.filter((step) => !step.active && step.display !== "none" && step.height > 0);
    if (activeVisible.length !== 1 || inactiveVisible.length) {
      throw new Error(`${caseId} viewport ${viewport}: single active step invariant failed`);
    }
  }
  if (!["walkthrough", "module_grid"].includes(caseType)) {
    throw new Error(`${caseId}: unsupported type ${caseType}`);
  }
}

async function waitForChrome(port) {
  const endpoint = `http://127.0.0.1:${port}/json/list`;
  for (let i = 0; i < 80; i += 1) {
    try {
      const targets = await httpGetJson(endpoint);
      const page = Array.isArray(targets) ? targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl) : null;
      if (page) return page;
    } catch {
    }
    await sleep(100);
  }
  throw new Error("Chrome page DevTools endpoint did not become available");
}

async function runWithChrome(chromePath, callback) {
  const port = 9222 + Math.floor(Math.random() * 1000);
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "svgflow-chrome-"));
  const chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ], { stdio: "ignore" });

  try {
    const pageTarget = await waitForChrome(port);
    const socket = await connectWebSocket(pageTarget.webSocketDebuggerUrl);
    const client = createCdpClient(socket);
    await client.send("Runtime.enable");
    await client.send("Page.enable");
    try {
      await callback(client);
    } finally {
      client.close();
    }
  } finally {
    chrome.kill("SIGTERM");
    await waitForProcessExit(chrome);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      try {
        fs.rmSync(userDataDir, { recursive: true, force: true });
        break;
      } catch (error) {
        if (attempt === 4) throw error;
        await sleep(100);
      }
    }
  }
}

async function evaluateCase(client, root, testCase) {
  const caseId = testCase.id;
  const fixture = path.join(root, testCase.fixture);
  if (!fs.existsSync(fixture)) throw new Error(`${caseId}: fixture not found: ${fixture}`);
  const fragment = fs.readFileSync(fixture, "utf8");
  const harness = makeHarness(fragment, caseId);
  const htmlPath = path.join(os.tmpdir(), `svgflow-${process.pid}-${caseId}.html`);
  fs.writeFileSync(htmlPath, harness, "utf8");
  const viewports = testCase.viewports || [720];
  const assertions = testCase.assertions || ["noHorizontalOverflow"];
  try {
    for (const viewport of viewports) {
      await client.send("Emulation.setDeviceMetricsOverride", {
        width: viewport,
        height: 900,
        deviceScaleFactor: 1,
        mobile: viewport <= 480,
      });
      await client.send("Page.navigate", { url: `file://${htmlPath}` });
      await sleep(250);
      const result = await client.send("Runtime.evaluate", {
        expression: metricExpression(testCase.type),
        returnByValue: true,
      });
      assertMetrics(caseId, viewport, testCase.type, assertions, result.result.value);
    }
  } finally {
    fs.rmSync(htmlPath, { force: true });
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const root = path.resolve(args.root);
  const casesPath = path.resolve(root, args.cases);
  if (!fs.existsSync(casesPath)) fail(`Missing cases file: ${casesPath}`);
  const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));
  const chromePath = findChrome(args.chrome);
  if (!chromePath) {
    fail("Chrome/Chromium not found. Set CHROME_PATH or pass --chrome.");
  }

  await runWithChrome(chromePath, async (client) => {
    for (const testCase of cases.valid || []) {
      await evaluateCase(client, root, testCase);
    }
    for (const testCase of cases.invalid || []) {
      let failed = false;
      let message = "";
      const invalidAssertions = testCase.type === "walkthrough"
        ? ["noHorizontalOverflow", "svgVisible", "singleActiveStep", "clickTargets"]
        : ["noHorizontalOverflow", "cardsVisible", "clickTargets"];
      try {
        await evaluateCase(client, root, {
          assertions: invalidAssertions,
          ...testCase,
        });
      } catch (error) {
        failed = true;
        message = error.message;
      }
      if (!failed) {
        throw new Error(`${testCase.id}: invalid fixture passed browser render metrics`);
      }
      if (!message.includes(testCase.expectedFailure)) {
        throw new Error(`${testCase.id}: expected failure not found: ${testCase.expectedFailure}; actual: ${message}`);
      }
    }
  });
  ok(`Browser render metric checks passed: ${path.relative(root, casesPath)}`);
}

main().catch((error) => fail(error.message));
