const $ = (id) => document.getElementById(id);

const DEFAULT_API = "http://localhost:8000";

const HOSTS = {
  greenhouse: /(^|\.)greenhouse\.io$/,
  lever: /(^|\.)lever\.(co|io|us)$/,
  ashby: /(^|\.)ashbyhq\.com$/,
};

const VIEWS = ["signin", "profile", "unsupported", "noform", "detected", "filled", "error"];

function show(...names) {
  for (const v of VIEWS) {
    const el = $("view-" + v);
    if (el) el.hidden = !names.includes(v);
  }
}

function setStatus(kind, text) {
  const el = $("status-dot");
  el.classList.remove("ok", "warn", "off");
  el.classList.add(kind);
  el.querySelector(".t").textContent = text;
}

function send(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

function sendToTab(tabId, msg) {
  return new Promise((resolve) => {
    try {
      chrome.tabs.sendMessage(tabId, msg, (resp) => {
        if (chrome.runtime.lastError) resolve(null);
        else resolve(resp);
      });
    } catch {
      resolve(null);
    }
  });
}

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function apiBase() {
  const { api_base } = await chrome.storage.local.get("api_base");
  return api_base || DEFAULT_API;
}

function hostKind(url) {
  try {
    const u = new URL(url);
    for (const [k, re] of Object.entries(HOSTS)) {
      if (re.test(u.hostname)) return k;
    }
  } catch {}
  return null;
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

function initials(name) {
  if (!name) return "—";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "—";
}

async function renderProfile() {
  const resp = await send({ type: "api", path: "/api/extension/profile", method: "GET" });
  if (!resp?.ok) return null;
  const p = resp.data || {};
  const name = [p.first_name, p.last_name].filter(Boolean).join(" ") || p.name || "Your profile";
  const email = p.email || "";
  $("pname").textContent = name;
  $("pemail").textContent = email;
  $("avatar").textContent = initials(name);
  $("view-profile").hidden = false;
  return p;
}

async function renderSignedOut() {
  const base = await apiBase();
  $("signin-btn").href = `${base}/signup`;
  $("dashboard-link").href = `${base}/app`;
  setStatus("off", "Signed out");
  show("signin");
}

async function renderSignedIn(tab) {
  const base = await apiBase();
  $("dashboard-link").href = `${base}/app`;
  setStatus("ok", "Connected");

  const profile = await renderProfile();
  if (!profile) {
    return renderSignedOut();
  }

  const kind = hostKind(tab?.url || "");
  if (!kind) {
    show("profile", "unsupported");
    return;
  }

  const det = await sendToTab(tab.id, { type: "content:detect" });
  if (!det?.ok || !det.hasForm) {
    show("profile", "noform");
    return;
  }

  $("detect-adapter").textContent = capitalize(det.adapter || kind);
  $("field-count").textContent = det.fieldCount != null ? String(det.fieldCount) : "Some";
  show("profile", "detected");
}

async function onFill() {
  const tab = await currentTab();
  const btn = $("fill-btn");
  btn.disabled = true;
  btn.textContent = "Filling…";
  const resp = await sendToTab(tab.id, { type: "content:fillStandard" });
  btn.disabled = false;
  btn.textContent = "Fill standard fields";

  if (!resp?.ok) {
    $("err-msg").textContent = resp?.error || "Unknown error. Try reloading the page.";
    show("profile", "error");
    return;
  }
  $("n-filled").textContent = resp.filled?.length ?? 0;
  $("n-skipped").textContent = resp.skipped?.length ?? 0;
  $("n-unknown").textContent = resp.unknown?.length ?? 0;
  show("profile", "filled");
}

async function onFillCustom() {
  const tab = await currentTab();
  const btn = $("fill-custom-btn");
  btn.disabled = true;
  btn.textContent = "AI working…";
  const resp = await sendToTab(tab.id, { type: "content:fillCustom" });
  btn.disabled = false;
  btn.textContent = "Fill custom answers (AI)";

  if (!resp?.ok) {
    $("err-msg").textContent = resp?.error || "AI autofill failed. Try again.";
    show("profile", "error");
    return;
  }

  // Show custom results in the filled view
  const customDiv = $("custom-results");
  if (customDiv) {
    customDiv.hidden = false;
    $("n-custom-filled").textContent = resp.filled?.length ?? 0;
    $("n-custom-skipped").textContent = resp.skipped?.length ?? 0;
  }

  // Stay in filled view
  $("n-filled").textContent = resp.filled?.length ?? 0;
  $("n-skipped").textContent = resp.skipped?.length ?? 0;
  $("n-unknown").textContent = resp.unknown?.length ?? 0;
  show("profile", "filled");
}

async function init() {
  const tab = await currentTab();
  const { signedIn } = await send({ type: "auth:status" });
  if (!signedIn) {
    await renderSignedOut();
  } else {
    await renderSignedIn(tab);
  }
}

$("fill-btn").addEventListener("click", onFill);
$("fill-custom-btn").addEventListener("click", onFillCustom);
$("refill-btn").addEventListener("click", onFill);
$("retry-btn").addEventListener("click", init);
$("signout-link").addEventListener("click", async (e) => {
  e.preventDefault();
  await send({ type: "auth:signOut" });
  init();
});

init();
